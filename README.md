# srw2ho iothub2ppmpconnector Library

### Installation from Repository (online)
```bash
pip install git+github.com/srw2ho/iothub2ppmpconnector.git
```

### Bundle python and project into .exe
```bash
pyinstaller iothub2ppmpconnector.spec --onefile --clean
```

### Configuration
The configuration file has to be stored as "../appwindowsconfigs/iothub2ppmpconnector.toml": for windows
The configuration file has to be stored as "/etc/appwindowsconfigs/iothub2ppmpconnector.toml": for docker


```toml
[mqtt]

host = "localhost"
port = 1883
username = ""
password = ""

[iothub]
# az iot hub show --query properties.eventHubEndpoints.events.endpoint --name {your IoT Hub name}

# az iot hub show --query properties.eventHubEndpoints.events.path --name {your IoT Hub name}


# Primary key for the "service" policy to read messages
# az iot hub policy show --name service --query primaryKey --hub-name {your IoT Hub name}


CONNECTION_STR = ""

### Usage
```bash
python -m iothub2ppmpconnector
```

# Build Docker
    docker build . -t iothub2ppmpconnector

# run Docker
    docker run --rm -i -t iothub2ppmpconnector /bin/sh