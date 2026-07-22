import ast

from output_generators.logger import logger
import technology_specific_extractors.aws_messaging.aws_entry as aws
import technology_specific_extractors.aws_services.aws_svc_entry as awssvc
import technology_specific_extractors.http_server.hsv_entry as hsv
import technology_specific_extractors.crypto_inventory.cry_entry as cry
import technology_specific_extractors.http_client.hcl_entry as hcl
import technology_specific_extractors.databases_node.dbn_entry as dbn
import technology_specific_extractors.kafka_node.kfn_entry as kfn
import technology_specific_extractors.rabbitmq_node.rmn_entry as rmn
import technology_specific_extractors.bullmq_node.bmq_entry as bmq
import technology_specific_extractors.database_connections.dbc_entry as dbc
import technology_specific_extractors.docker_compose.dcm_entry as dcm
import technology_specific_extractors.feign_client.fgn_entry as fgn
import technology_specific_extractors.gradle.grd_entry as grd
import technology_specific_extractors.html.html_entry as html
import technology_specific_extractors.implicit_connections.imp_entry as imp
import technology_specific_extractors.kafka.kfk_entry as kfk
import technology_specific_extractors.maven.mvn_entry as mvn
import technology_specific_extractors.nodejs.npm_entry as npm
import technology_specific_extractors.rabbitmq.rmq_entry as rmq
import technology_specific_extractors.resttemplate.rst_entry as rst
import tmp.tmp as tmp


def get_microservices(dfd) -> dict:
    """Calls get_microservices from correct container technology or returns existing list.
    """

    if tmp.tmp_config.has_option("DFD", "microservices"):
        return ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])
    else:
        logger.info("Microservices not set yet, start extraction")

        mvn.set_microservices(dfd)
        grd.set_microservices(dfd)
        dcm.set_microservices(dfd)
        npm.set_microservices(dfd)
        if tmp.tmp_config.has_option("DFD", "microservices"):
            return ast.literal_eval(tmp.tmp_config["DFD"]["microservices"])


def get_information_flows(dfd) -> dict:
    """Calls get_information_flows from correct communication technology.
    """

    if tmp.tmp_config.has_option("DFD", "information_flows"):
        return ast.literal_eval(tmp.tmp_config["DFD"]["information_flows"])
    else:
        logger.info("Information flows not set yet, start extraction")
        communication_techs_list = ast.literal_eval(tmp.tmp_config["Technology Profiles"]["communication_techs_list"])
        for com_tech in communication_techs_list:
            eval(com_tech[1]).set_information_flows(dfd)

        if tmp.tmp_config.has_option("DFD", "information_flows"):
            return ast.literal_eval(tmp.tmp_config["DFD"]["information_flows"])


def detect_microservice(file_path: str, dfd) -> str:
    """Calls detect_microservices from correct microservice detection technology.
    """

    microservice = mvn.detect_microservice(file_path, dfd)
    if not microservice:
        microservice = grd.detect_microservice(file_path, dfd)
    if not microservice:
        microservice = dcm.detect_microservice(file_path, dfd)
    if not microservice:
        microservice = npm.detect_microservice(file_path, dfd)
    return microservice
