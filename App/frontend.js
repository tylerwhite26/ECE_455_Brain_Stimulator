// Update the beat frequency output based on the input frequencies
function updateBeatOutput() {
    const freq1 = parseFloat(document.getElementById('frequency_1').value) || 0;
    const freq2 = parseFloat(document.getElementById('frequency_2').value) || 0;
    const beat = Math.abs(freq1 - freq2);
    document.getElementById('beat_calc').value = `${beat}`;
}

// Call updateBeatOutput() whenever the input values change
document.getElementById('frequency_1').addEventListener('input', updateBeatOutput);
document.getElementById('frequency_2').addEventListener('input', updateBeatOutput);

// Call once on page load
updateBeatOutput();

var connected_device = null;
var prime_serv = null;
var ble_char = null;

// Function to connect to Bluetooth device
function startBluetooth() {
    navigator.bluetooth.getAvailability().then((available) => {
        if (!available) {
            alert("Web Bluetooth is not supported on this browser.");
            return;
        }

        let options = {
            filters: [
                { name: "mpy-uart" },
            ],
            optionalServices: ['6e400001-b5a3-f393-e0a9-e50e24dcca9e']
        };

        navigator.bluetooth
            .requestDevice(options)
            .then((device) => {
                console.log(`Connected to: ${device.name}`);
                connected_device = device;
                return connected_device.gatt.connect();
            })
            .then((gatt) => {
                console.log("GATT connected");
                return gatt.getPrimaryService('6e400001-b5a3-f393-e0a9-e50e24dcca9e');
            })
            .then((service) => {
                console.log("Service found");
                prime_serv = service;
                // 6e400002 is typically the TX characteristic (write to device)
                // 6e400003 is typically the RX characteristic (read from device)
                return prime_serv.getCharacteristic('6e400002-b5a3-f393-e0a9-e50e24dcca9e');
            })
            .then((characteristic) => {
                console.log("Characteristic found, connection successful!");
                ble_char = characteristic;
                document.getElementById("connection_status").innerText = `Connected`;
                document.getElementById("connection_status").className = `conn-good`;
            })
            .catch((error) => {
                console.error(`Connection failed: ${error}`);
                document.getElementById("connection_status").innerText = `Failed`;
                document.getElementById("connection_status").className = `conn-bad`;
            });
    });
}

// Method for writing to the device
function writeToDevice(message) {
    if (ble_char == null) {
        alert("Device not connected. Please connect to a device first.");
        return;
    }
    
    console.log(`Sending: ${message}`);
    
    // Encode the message as Uint8Array
    let data;
    if (typeof message === 'string') {
        data = new TextEncoder().encode(message);
    } else if (message instanceof ArrayBuffer) {
        data = new Uint8Array(message);
    } else {
        data = message;
    }
    
    ble_char.writeValueWithoutResponse(data)
        .then(() => console.log("Written to device successfully"))
        .catch((error) => console.error(`Write failed: ${error}`));
}

// Send frequency 1
function sendFrequency1() {
    const freq1 = parseFloat(document.getElementById('frequency_1').value);
    if (isNaN(freq1)) {
        alert("Please enter a valid frequency");
        return;
    }
    const message = `${freq1}\n`;
    writeToDevice(message);
}

// Send frequency 2
function sendFrequency2() {
    const freq2 = parseFloat(document.getElementById('frequency_2').value);
    if (isNaN(freq2)) {
        alert("Please enter a valid frequency");
        return;
    }
    const message = `${freq2}\n`;
    writeToDevice(message);
}

// Program device with both frequencies
function programDevice() {
    const freq1 = parseFloat(document.getElementById('frequency_1').value);
    const freq2 = parseFloat(document.getElementById('frequency_2').value);
    
    if (isNaN(freq1) || isNaN(freq2)) {
        alert("Please enter valid frequencies");
        return;
    }
    
    const message = `${freq1},${freq2}\n`;
    writeToDevice(message);
}