import asyncio
from azure.eventhub import TransportType
from azure.eventhub.aio import EventHubConsumerClient
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
import json
# from mhopcua.opc_ua import OPCUAServer
from mqttconnector.client import MQTTClient
from ppmpmessage.v3.device_state import DeviceState
from ppmpmessage.v3.device import Device
from ppmpmessage.v3.util import machine_message_generator
from ppmpmessage.v3.util import local_now
from ppmpmessage.convertor.simple_variables import SimpleVariables
from ppmpmessage.v3.device import Device
from ppmpmessage.v3.device import iotHubDevice

from pathlib import Path
from threading import Thread
from tomlconfig.tomlutils import TomlParser
from datetime import datetime

PROJECT_NAME = 'iothub2ppmpconnector'

# load configuration from config file
toml = TomlParser(f'{PROJECT_NAME}.toml')

# Event Hub-compatible endpoint
# az iot hub show --query properties.eventHubEndpoints.events.endpoint --name {your IoT Hub name}
# EVENTHUB_COMPATIBLE_ENDPOINT = "{your Event Hubs compatible endpoint}"
EVENTHUB_COMPATIBLE_ENDPOINT =  toml.get("iothub.EVENTHUB_COMPATIBLE_ENDPOINT", "")
# Event Hub-compatible name
# az iot hub show --query properties.eventHubEndpoints.events.path --name {your IoT Hub name}
# EVENTHUB_COMPATIBLE_PATH = "{your Event Hubs compatible name}"
EVENTHUB_COMPATIBLE_PATH = toml.get("iothub.EVENTHUB_COMPATIBLE_PATH","")
# Primary key for the "service" policy to read messages
# az iot hub policy show --name service --query primaryKey --hub-name {your IoT Hub name}
IOTHUB_SAS_KEY = toml.get("iothub.IOTHUB_SAS_KEY","")


# EVENTHUB_COMPATIBLE_ENDPOINT = "sb://ihsuprodamres068dednamespace.servicebus.windows.net/"
# EVENTHUB_COMPATIBLE_PATH = "iothub-ehub-srw2ho-iot-5365396-53338a5198"
# IOTHUB_SAS_KEY = "n0cZaxLPmutlFt3wrzfvV3htQAfiqxr5pBienbTlxW0="
# If you have access to the Event Hub-compatible connection string from the Azure portal, then
# you can skip the Azure CLI commands above, and assign the connection string directly here.
CONNECTION_STR = f'Endpoint={EVENTHUB_COMPATIBLE_ENDPOINT}/;SharedAccessKeyName=service;SharedAccessKey={IOTHUB_SAS_KEY};EntityPath={EVENTHUB_COMPATIBLE_PATH}'


MQTT_ENABLED = toml.get('mqtt.enabled', True)
MQTT_NETWORK_NAME = toml.get('mqtt.network_name', 'mh')
MQTT_HOST = toml.get('mqtt.host', 'localhost')
MQTT_PORT = toml.get('mqtt.port', 1883)
MQTT_USERNAME = toml.get('mqtt.username', '')
MQTT_PASSWORD = toml.get('mqtt.password', '')
MQTT_TLS_CERT = toml.get('mqtt.tls_cert', '')

LOGFOLDER = "./logs/"

# DEVICE_GATEWAY = Device(
#     additionalData={
#         'type': 'OPC_UA_GATEWAY',
#     },
# )
# DEVICE_PLC = Device(
#     additionalData={
#         'type': 'iotHub',
#     },
# )


# configure logging
logger = logging.getLogger('root')
logger.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

try:  
    os.mkdir(LOGFOLDER)
    logger.info(f'create logfolder: {LOGFOLDER}')
except OSError as error:  
    logger.info(f'create logfolder: {LOGFOLDER}:{error}')
# fl = logging.FileHandler('OPC-UA.log')
# Rotation file handler miit 200 000 bytes pro file und 10 files in rotation
fl = RotatingFileHandler(f'{LOGFOLDER}{PROJECT_NAME}.log',mode='a', maxBytes=2*(10**5), backupCount=10)
fl.setLevel(logging.ERROR)
fl.setFormatter(formatter)
logger.addHandler(fl)


# # list of all OPC-UA client processes
# threads = []
# processes = []

globMQTTClient = None
iothubdevices = dict()


def sendMQTTPayload(event):
    global iothubdevices
    global globMQTTClient
    
    jsonpayload = event.body_as_json(encoding='UTF-8')
    acttime = local_now()
    # if event.system_properties[b'x-opt-enqueued-time']: acttime = event.system_properties[b'x-opt-enqueued-time']
    if event.system_properties[b'iothub-connection-device-id']: deviceId = event.system_properties[b'iothub-connection-device-id']
    
    if globMQTTClient!=None:  
        iotDevice = iothubdevices.get(deviceId)
    
        if iotDevice==None: 
            iotDevice =iotHubDevice(net_name='mh', devideid= deviceId, additionalData={'type': 'iotHub', },)
            iothubdevices[deviceId] = iotDevice
            globMQTTClient.publish(iotDevice.info_topic(), machine_message_generator(iotDevice),retain=True)

        simplevars = SimpleVariables(iotDevice, jsonpayload, acttime)
        ppmppayload = simplevars.to_ppmp()
                
        if globMQTTClient.isConnected:
            globMQTTClient.publish(iotDevice.ppmp_topic(), ppmppayload, retain=True)
        
        logger.info (f'MQTT-PPMP-Payload device:{iotDevice.getHostname()}:{ppmppayload}')

# Define callbacks to process events
async def on_event_MQTTPayload(partition_context, events):
    try:

        for event in events:
            # print("Received event from partition: {}.".format(partition_context.partition_id))
            # print("Telemetry received: ", event.body_as_str())
            # print("Properties (set by device): ", event.properties)
            # print("System properties (set by IoT Hub): ", event.system_properties)
            sendMQTTPayload(event)

  
    except Exception as e:
            logger.error (f'on_event_MQTTPayload:{e}')
    finally:
        await partition_context.update_checkpoint()

async def on_error(partition_context, error):
    # Put your code here. partition_context can be None in the on_error callback.
    if partition_context:
        logger.error (f'An exception: {partition_context.partition_id} occurred during receiving from Partition: {error}.')

        logger.info (f'An exception: {partition_context.partition_id} occurred during receiving from Partition: {error}.')
        # print("An exception: {} occurred during receiving from Partition: {}.".format(
        #     partition_context.partition_id,
        #     error
        # ))
    else:
        logger.error (f'An exception: {error} occurred during the load balance process.')
        logger.info (f'An exception: {error} occurred during the load balance process.')
        # print("An exception: {} occurred during the load balance process.".format(error))



def start_azureiothub():
    global globMQTTClient
    # send complete config list for all devices (as gateway, not only single PLC device)
    globMQTTClient = MQTTClient(host=MQTT_HOST, port=MQTT_PORT, user=MQTT_USERNAME, password=MQTT_PASSWORD, tls_cert=MQTT_TLS_CERT)

    # create machine message with state ERROR (LWT) (do this before(!) connect)
    # globMQTTClient.last_will(
    #     DEVICE_PLC.info_topic(),
    #     machine_message_generator(DEVICE_PLC, state=DeviceState.ERROR, code="offline"),
    #     retain=True
    # )

    # connect to MQTT
    globMQTTClient.connect()

    # register via PPMP as "Gateway device"
    # create machine message with state=ON and code=online (retain)
    # globMQTTClient.publish(
    #     DEVICE_PLC.info_topic(),
    #     machine_message_generator(DEVICE_PLC),
    #     retain=True
    # )

    loop = asyncio.get_event_loop()
    client = EventHubConsumerClient.from_connection_string(
        conn_str=CONNECTION_STR,
        consumer_group="$default",
        # transport_type=TransportType.AmqpOverWebsocket,  # uncomment it if you want to use web socket
        # http_proxy={  # uncomment if you want to use proxy 
        #     'proxy_hostname': '127.0.0.1',  # proxy hostname.
        #     'proxy_port': 3128,  # proxy port.
        #     'username': '<proxy user name>',
        #     'password': '<proxy password>'
        # }
    )
    try:
        loop.run_until_complete(client.receive_batch(on_event_batch=on_event_MQTTPayload, on_error=on_error))
    except KeyboardInterrupt:
        print("Receiving has stopped.")
    finally:
        loop.run_until_complete(client.close())
        loop.stop()

    # subscribe to commands that are sent from broker to the OPC-UA interface
    # mqtt_client.subscribe(DEVICE_GATEWAY.control_set_topic(), handle_mqtt_commands)

   


def restart_opcua():
    os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)
    sys.exit(0) 


def main():

    # start start_azureiothub (and start mqtt-connection)
    
    start_azureiothub()

if __name__ == '__main__':
    main()
