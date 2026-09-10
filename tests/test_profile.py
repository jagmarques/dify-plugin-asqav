"""Profile observations preserve evidence and never grant execution authority."""
import hashlib
import json

import httpx
import pytest

from tools._profile import canonical, profile_request, strict_object
from tools._verification import hosted_evidence
from tools.sign_action import SignActionTool
from tools.verify_signature import VerifySignatureTool
from tests.test_tools_smoke import _make_tool, _json_and_var_names

PARAMETERS = {'action_type': 'read:data', 'context': '{"item":1}',
              'receipt_mode': 'profile', 'iteration_id': 'workflow-run-1'}


def response_body(body):
    context = canonical(body['context'])
    payload = {'v': 1, 'action_id': 'act_1', 'agent_id': 'agt_fixture', 'org_id': 'org_fixture',
               'issuer_id': 'did:example:issuer', 'mode': 'payload', 'type': 'protectmcp:lifecycle',
               'decision': 'observation', 'issued_at': '2026-09-10T00:00:00Z',
               'timestamp': '2026-09-10T00:00:00Z', 'policy_digest': 'sha256:'+'a'*64,
               'previousReceiptHash': 'b'*64, 'seq': 1, 'key_thumbprint': 'sha256:'+'c'*64,
               'payload_digest': {'hash': hashlib.sha256(context).hexdigest(), 'size': len(context)},
               **{k: body[k] for k in ('action_type','action_ref','iteration_id')}}
    return {'signature_id':'sig_1','action_id':'act_1','timestamp':1788998400.,
            'verification_url':'https://api.asqav.com/api/v1/verify/sig_1',
            'payload':payload,'signature':{'alg':'ML-DSA-65','kid':payload['issuer_id'],'sig':'fixture=='},
            'anchors':[], 'anchor_pending':True, 'decision':'observation',
            'policy_decision':'none','policy_enforcement':None}


def invoke(mocker, data, parameters=None, status=200):
    response = httpx.Response(status, json=data, request=httpx.Request('POST','https://example.invalid'))
    post = mocker.patch('tools.sign_action.httpx.post', return_value=response)
    tool = _make_tool(SignActionTool, {'asqav_api_key':'fixture','asqav_agent_id':'agt_fixture'})
    messages = list(tool._invoke(PARAMETERS if parameters is None else parameters))
    return _json_and_var_names(messages)[0][0].message.json_object, post


@pytest.mark.parametrize('status,pending', [(200,False),(200,True),(202,False)])
def test_profile_observation_roundtrip_never_authorizes(mocker,status,pending):
    body=profile_request(PARAMETERS, PARAMETERS['action_type'])
    data=response_body(body);data['anchor_pending']=pending
    data['anchors']=[{'type':'rfc3161','value':'fixture'}]
    result,post=invoke(mocker,data,status=status)
    assert post.call_args.kwargs['json']==body
    assert body['capture_topology']=='in_process_sdk'
    assert body['policy_decision']=='none'
    assert result['authorized'] is False
    assert result['anchor_pending'] is (status==202 or pending)
    assert result['receipt']=={k:data[k] for k in ('payload','signature','anchors')}
    assert json.loads(result['receipt_json'])==result['receipt']
    assert result['action_ref']==body['action_ref']


@pytest.mark.parametrize('context', ['{"x":1,"x":2}','{"nested":{"x":1,"x":2}}',
    '{"x":NaN}','{"x":Infinity}','{"x":1.0}','{"x":9007199254740992}',
    '{"x":-9007199254740992}','[]','null','true','not-json', '{"x":"\\ud800"}',
    '{"x":'+'['*66+'0'+']'*66+'}', '{"x":"'+'a'*1048576+'"}'])
def test_invalid_profile_context_never_sends(mocker,context):
    post=mocker.patch('tools.sign_action.httpx.post')
    tool=_make_tool(SignActionTool, {'asqav_api_key':'fixture','asqav_agent_id':'agt_fixture'})
    with pytest.raises((ValueError,UnicodeError)):
        list(tool._invoke({**PARAMETERS,'context':context}))
    post.assert_not_called()


@pytest.mark.parametrize('field,value',[('iteration_id',''),('iteration_id','a'*129),
    ('action_ref','arbitrary'),('receipt_mode','unknown')])
def test_invalid_profile_parameters_never_send(mocker,field,value):
    post=mocker.patch('tools.sign_action.httpx.post')
    tool=_make_tool(SignActionTool, {'asqav_api_key':'fixture','asqav_agent_id':'agt_fixture'})
    with pytest.raises(ValueError):list(tool._invoke({**PARAMETERS,field:value}))
    post.assert_not_called()


@pytest.mark.parametrize('key,value', [('agent_id','agt_other'),('action_type','write:data'),
    ('action_ref','sha256:'+'e'*64),('iteration_id','other-run'),('action_id','act_other'),
    ('mode','hash'),('v',True),('v',2),('decision','allow'),('type','protectmcp:decision'),
    ('issuer_id','did:example:other'),('payload_digest',{'hash':'bad','size':1})])
def test_swapped_or_malformed_signed_response_has_no_output(mocker,key,value):
    data=response_body(profile_request(PARAMETERS,PARAMETERS['action_type']))
    data['payload'][key]=value
    with pytest.raises(ValueError):invoke(mocker,data)


@pytest.mark.parametrize('key,value',[('payload',None),('signature','fixture'),('anchors',{}),
    ('anchors',[None]),('anchor_pending','true'),('decision','allow'),('policy_decision','permit'),
    ('signature',{'alg':'ML-DSA-65','kid':'other','sig':'fixture'}),('signature',{})])
def test_invalid_envelope_or_metadata_has_no_output(mocker,key,value):
    data=response_body(profile_request(PARAMETERS,PARAMETERS['action_type']));data[key]=value
    with pytest.raises(ValueError):invoke(mocker,data)


@pytest.mark.parametrize('status',[401,412,422,429,503])
def test_profile_errors_never_fall_back_to_standard(mocker,status):
    with pytest.raises(httpx.HTTPStatusError):invoke(mocker,{'detail':'unavailable'},status=status)
    assert httpx.post.call_count == 1


def test_canonical_action_uses_utf16_order_and_safe_boundary():
    context={'\ue000':9007199254740991,'\U0001f600':-9007199254740991}
    value=canonical(context)
    assert value==('{"😀":-9007199254740991,"\ue000":9007199254740991}').encode()
    body=profile_request({**PARAMETERS,'context':json.dumps(context)},'read:data')
    expected=b'{"action_type":"read:data","context":'+value+b'}'
    assert body['action_ref']=='sha256:'+hashlib.sha256(expected).hexdigest()
    assert profile_request({**PARAMETERS,'action_ref':profile_request(PARAMETERS,'read:data')['action_ref']},'read:data')


def test_nested_json_domain_and_size_guards():
    assert strict_object('{"nested":[{"ok":true},null]}')=={'nested':[{'ok':True},None]}
    with pytest.raises(ValueError):strict_object(1)
    with pytest.raises(ValueError):strict_object('{"x":'+'['*1500+'0'+']'*1500+'}')


def hosted():
    return {'verified':True,'signature_id':'sig_1','agent_id':None,'agent_name':None,
            'action_type':None,'algorithm':'ML-DSA-65','signed_at':'2026-09-10T00:00:00Z',
            'verification_url':'https://example.invalid','anchor_confirmed':False,
            'execution_evidence':None,'stale_pending':False,
            'verification_detail':{'signature_valid':True,'signer_key_match':True,
                'algorithm_match':True,'chain_valid':False,'anchor_valid_ots':None,
                'anchor_valid_rfc3161':None,'validation_label':'expired','failure_class':'invalid'}}


def test_hosted_signature_rollup_never_becomes_profile_pass(mocker):
    data=hosted()
    get=mocker.patch('tools.verify_signature.httpx.get',return_value=httpx.Response(200,json=data,
        request=httpx.Request('GET','https://example.invalid')))
    tool=_make_tool(VerifySignatureTool,{})
    result=_json_and_var_names(list(tool._invoke({'signature_id':'sig_1'})))[0][0].message.json_object
    assert result['verified'] is True
    assert result['profile_verdict']=='unverified'
    assert result['verification_detail']==data['verification_detail']
    assert result['signature_valid'] is True and result['anchor_confirmed'] is False
    assert 'headers' not in get.call_args.kwargs


@pytest.mark.parametrize('field,value',[('verification_detail',[]),('stale_pending','false'),
    ('anchor_confirmed',1),('execution_evidence',[])])
def test_bad_hosted_evidence_is_not_coerced(field,value):
    data=hosted();data[field]=value
    with pytest.raises(ValueError):hosted_evidence(data)


@pytest.mark.parametrize('field,value',[('signature_valid','true'),('chain_valid',1),
    ('anchor_valid_ots',[]),('failure_class','unknown')])
def test_bad_hosted_axes_are_rejected(field,value):
    data=hosted();data['verification_detail'][field]=value
    with pytest.raises(ValueError):hosted_evidence(data)


def test_missing_hosted_axes_remain_unavailable():
    assert hosted_evidence({})['profile_failure_class']=='unverifiable'
    data=hosted();data['verification_detail']={};data['stale_pending']=None
    result=hosted_evidence(data)
    assert result['signature_valid'] is None and result['stale_pending'] is None
    assert result['profile_verdict']=='unverified'


def test_hosted_response_must_match_requested_signature(mocker):
    data=hosted();data['signature_id']='sig_other'
    mocker.patch('tools.verify_signature.httpx.get',return_value=httpx.Response(200,json=data,
        request=httpx.Request('GET','https://example.invalid')))
    tool=_make_tool(VerifySignatureTool,{})
    with pytest.raises(ValueError,match='different signature ID'):
        list(tool._invoke({'signature_id':'sig_1'}))


@pytest.mark.parametrize('raw',['{"payload":{},"payload":{}}','[1]','NaN','not-json',
    '{"payload":'+ '['*1500+'0'+']'*1500+'}', '"'+'a'*1048576+'"'])
def test_profile_response_parser_refuses_ambiguous_json(raw):
    from tools._profile import profile_response
    with pytest.raises(ValueError):profile_response(raw)


def bound_response(receipt, **changes):
    import hashlib
    from tools._verification import _REQUIRED_CHECKS
    result={'verdict':'pass','wire_verdict':'verified','failure_class':None,
        'format':'asqav-native','signature_valid':True,'profile_verification':{
            'verdict':'verified','failure_class':None,
            'receipt_digest':'sha256:'+hashlib.sha256(canonical(receipt)).hexdigest(),
            'checks':{k:'pass' for k in _REQUIRED_CHECKS},'expired':False,
            'duplicate_emission_candidate':False,'anchor_valid_ots':True,'anchor_valid_rfc3161':False}}
    result.update(changes)
    return result


def test_exact_receipt_uses_bound_endpoint_without_credentials(mocker):
    receipt={'payload':{'v':1},'signature':{'alg':'ML-DSA-65'},'anchors':[]}
    post=mocker.patch('tools.verify_signature.httpx.post',return_value=httpx.Response(200,json=bound_response(receipt),
        request=httpx.Request('POST','https://example.invalid')))
    get=mocker.patch('tools.verify_signature.httpx.get')
    tool=_make_tool(VerifySignatureTool,{})
    original=json.dumps(receipt,indent=2)
    result=_json_and_var_names(list(tool._invoke({'signature_id':'sig_1','receipt_json':original})))[0][0].message.json_object
    assert result['verified'] is True and result['authorized'] is False
    assert result['receipt_json']==original and result['anchors_refreshed'] is False
    assert post.call_args.kwargs['json']['signature_id']=='sig_1'
    assert 'headers' not in post.call_args.kwargs
    get.assert_not_called()


@pytest.mark.parametrize('mutation',['digest','missing_check','invalid_check','false_signature','false_pass','bad_flag'])
def test_bound_response_cannot_claim_incomplete_or_unbound_pass(mutation):
    from tools._verification import bound_evidence
    receipt={'payload':{},'signature':{}};data=bound_response(receipt)
    detail=data['profile_verification']
    if mutation=='digest':detail['receipt_digest']='sha256:'+'0'*64
    elif mutation=='missing_check':del detail['checks']['chain']
    elif mutation=='invalid_check':detail['checks']['sequence']='invalid'
    elif mutation=='false_signature':data['signature_valid']=False
    elif mutation=='false_pass':data['verdict']='incomplete'
    else:detail['expired']='false'
    with pytest.raises(ValueError):bound_evidence(data,receipt,False)


def test_refresh_preserves_original_and_checks_new_proof_bytes(mocker):
    old={'payload':{},'signature':{},'anchors':[]}
    updated={**old,'anchors':[{'type':'opentimestamps','value':'new proof'}]}
    mocker.patch('tools.verify_signature.httpx.get',return_value=httpx.Response(200,
        json={'signature_id':'sig_1', 'anchors':updated['anchors'],'payload':{'redacted':True}},
        request=httpx.Request('GET','https://example.invalid')))
    post=mocker.patch('tools.verify_signature.httpx.post',return_value=httpx.Response(200,json=bound_response(updated),
        request=httpx.Request('POST','https://example.invalid')))
    tool=_make_tool(VerifySignatureTool,{})
    result=_json_and_var_names(list(tool._invoke({'signature_id':'sig_1','receipt_json':json.dumps(old),
        'refresh_anchors':True,'context_json':'{"item":1}'})))[0][0].message.json_object
    assert json.loads(result['receipt_json'])==old
    assert json.loads(result['verified_receipt_json'])==updated
    assert result['anchors_refreshed'] is True
    assert post.call_args.kwargs['json']['context_json']=='{"item":1}'


def test_valid_anchor_is_not_vetoed_by_absent_other_anchor():
    from tools._verification import bound_evidence
    receipt={'payload':{},'signature':{}};data=bound_response(receipt)
    assert bound_evidence(data,receipt,False)['verified'] is True
    old=hosted();old['verification_detail'].update(failure_class=None,anchor_valid_ots=True,anchor_valid_rfc3161=False)
    assert hosted_evidence(old)['profile_failure_class']=='unverifiable'


def test_profile_denial_remains_false_without_partial_receipt(mocker):
    result,post=invoke(mocker,{'detail':'Agent is in quarantine'},status=403)
    assert result['authorized'] is False and result['reason']=='quarantine'
    assert 'receipt' not in result
    assert post.call_count==1


def test_carried_context_must_match_requested_context(mocker):
    data=response_body(profile_request(PARAMETERS,PARAMETERS['action_type']))
    data['payload']['context']={'item':2}
    with pytest.raises(ValueError,match='carried context'):invoke(mocker,data)


def test_pending_anchor_does_not_require_server_retry_flag(mocker):
    data=response_body(profile_request(PARAMETERS,PARAMETERS['action_type']))
    data['anchor_pending']=False
    data['anchors']=[{'type':'opentimestamps','value':'fixture','status':'pending'}]
    result,_=invoke(mocker,data)
    assert result['anchor_pending'] is True and result['authorized'] is False


def test_known_invalid_evidence_dominates_missing_checks():
    data=hosted()
    assert hosted_evidence(data)['profile_failure_class']=='invalid'
    data['verification_detail']={'signature_valid':False}
    assert hosted_evidence(data)['profile_failure_class']=='invalid'
