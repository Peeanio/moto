from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

VPC_CIDR = "10.0.0.0/16"
BAD_VPC = "vpc-deadbeef"
BAD_IGW = "igw-deadbeef"


@mock_aws
def test_igw_create_boto3():
    """internet gateway create"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    with pytest.raises(ClientError) as ex:
        client.create_internet_gateway(DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the CreateInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    igw = ec2.create_internet_gateway()
    assert igw.id.startswith("igw-")

    igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    assert len(igw["Attachments"]) == 0


@mock_aws
def test_igw_attach_boto3():
    """internet gateway attach"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)

    with pytest.raises(ClientError) as ex:
        vpc.attach_internet_gateway(InternetGatewayId=igw.id, DryRun=True)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the AttachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    vpc.attach_internet_gateway(InternetGatewayId=igw.id)

    igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    assert igw["Attachments"] == [{"State": "available", "VpcId": vpc.id}]


@mock_aws
def test_igw_attach_bad_vpc_boto3():
    """internet gateway fail to attach w/ bad vpc"""
    ec2 = boto3.resource("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()

    with pytest.raises(ClientError) as ex:
        igw.attach_to_vpc(VpcId=BAD_VPC)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidVpcID.NotFound"


@mock_aws
def test_igw_attach_twice_boto3():
    """internet gateway fail to attach twice"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc1 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    vpc2 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc1.id)

    with pytest.raises(ClientError) as ex:
        client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc2.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "Resource.AlreadyAssociated"


@mock_aws
def test_igw_detach_boto3():
    """internet gateway detach"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(
            InternetGatewayId=igw.id, VpcId=vpc.id, DryRun=True
        )
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DetachInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)
    igw = igw = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    assert len(igw["Attachments"]) == 0


@mock_aws
def test_igw_detach_wrong_vpc_boto3():
    """internet gateway fail to detach w/ wrong vpc"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc1 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    vpc2 = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc1.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc2.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "Gateway.NotAttached"


@mock_aws
def test_igw_detach_invalid_vpc_boto3():
    """internet gateway fail to detach w/ invalid vpc"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=BAD_VPC)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "Gateway.NotAttached"


@mock_aws
def test_igw_detach_unattached_boto3():
    """internet gateway fail to detach unattached"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)

    with pytest.raises(ClientError) as ex:
        client.detach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "Gateway.NotAttached"


@mock_aws
def test_igw_delete_boto3():
    """internet gateway delete"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", region_name="us-west-1")
    ec2.create_vpc(CidrBlock=VPC_CIDR)

    igw = ec2.create_internet_gateway()
    assert igw.id in [i["InternetGatewayId"] for i in (retrieve_all(client))]

    with pytest.raises(ClientError) as ex:
        client.delete_internet_gateway(InternetGatewayId=igw.id, DryRun=True)
    assert ex.value.response["Error"]["Code"] == "DryRunOperation"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 412
    assert (
        ex.value.response["Error"]["Message"]
        == "An error occurred (DryRunOperation) when calling the DeleteInternetGateway operation: Request would have succeeded, but DryRun flag is set"
    )

    client.delete_internet_gateway(InternetGatewayId=igw.id)
    assert igw.id not in [i["InternetGatewayId"] for i in (retrieve_all(client))]


@mock_aws
def test_igw_delete_attached_boto3():
    """internet gateway fail to delete attached"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw.id, VpcId=vpc.id)

    with pytest.raises(ClientError) as ex:
        client.delete_internet_gateway(InternetGatewayId=igw.id)
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "DependencyViolation"


@mock_aws
def test_igw_describe_boto3():
    """internet gateway fetch by id"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")
    igw = ec2.create_internet_gateway()
    igw_by_search = client.describe_internet_gateways(InternetGatewayIds=[igw.id])[
        "InternetGateways"
    ][0]
    assert igw.id == igw_by_search["InternetGatewayId"]


@mock_aws
def test_igw_describe_bad_id_boto3():
    """internet gateway fail to fetch by bad id"""
    client = boto3.client("ec2", "us-west-1")
    with pytest.raises(ClientError) as ex:
        client.describe_internet_gateways(InternetGatewayIds=[BAD_IGW])
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RequestId" in ex.value.response["ResponseMetadata"]
    assert ex.value.response["Error"]["Code"] == "InvalidInternetGatewayID.NotFound"


@mock_aws
def test_igw_filter_by_vpc_id_boto3():
    """internet gateway filter by vpc id"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw1.id, VpcId=vpc.id)

    result = client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc.id]}]
    )
    assert len(result["InternetGateways"]) == 1
    assert result["InternetGateways"][0]["InternetGatewayId"] == igw1.id


@mock_aws
def test_igw_filter_by_tags_boto3():
    """internet gateway filter by vpc id"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()
    tag_value = str(uuid4())
    igw1.create_tags(Tags=[{"Key": "tests", "Value": tag_value}])

    result = retrieve_all(client, [{"Name": "tag:tests", "Values": [tag_value]}])
    assert len(result) == 1
    assert result[0]["InternetGatewayId"] == igw1.id


@mock_aws
def test_igw_filter_by_internet_gateway_id_boto3():
    """internet gateway filter by internet gateway id"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    ec2.create_internet_gateway()

    result = client.describe_internet_gateways(
        Filters=[{"Name": "internet-gateway-id", "Values": [igw1.id]}]
    )
    assert len(result["InternetGateways"]) == 1
    assert result["InternetGateways"][0]["InternetGatewayId"] == igw1.id


@mock_aws
def test_igw_filter_by_attachment_state_boto3():
    """internet gateway filter by attachment state"""
    ec2 = boto3.resource("ec2", "us-west-1")
    client = boto3.client("ec2", "us-west-1")

    igw1 = ec2.create_internet_gateway()
    igw2 = ec2.create_internet_gateway()
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR)
    client.attach_internet_gateway(InternetGatewayId=igw1.id, VpcId=vpc.id)

    filters = [{"Name": "attachment.state", "Values": ["available"]}]
    all_ids = [igw["InternetGatewayId"] for igw in (retrieve_all(client, filters))]
    assert igw1.id in all_ids
    assert igw2.id not in all_ids


@mock_aws
def test_create_internet_gateway_with_tags():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")

    igw = ec2.create_internet_gateway(
        TagSpecifications=[
            {
                "ResourceType": "internet-gateway",
                "Tags": [{"Key": "test", "Value": "TestRouteTable"}],
            }
        ]
    )
    assert len(igw.tags) == 1
    assert igw.tags == [{"Key": "test", "Value": "TestRouteTable"}]


def retrieve_all(client, filters=[]):
    resp = client.describe_internet_gateways(Filters=filters)
    all_igws = resp["InternetGateways"]
    token = resp.get("NextToken")
    while token:
        resp = client.describe_internet_gateways(NextToken=token, Filters=filters)
        all_igws.extend(resp["InternetGateways"])
        token = resp.get("NextToken")
    return all_igws
