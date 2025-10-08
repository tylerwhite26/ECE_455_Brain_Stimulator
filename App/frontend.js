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

// function to connect bluetooth and set device
function startBluetooth() {
    var can_support = navigator.bluetooth.getAvailability();
    if (!can_support) {
        alert("Web Bluetooth is not supported on this browser.");
        return;
    }

    // from mozilla web docs
    // let options = {
    //     filters: [
    //         { manufacturerData: [{
    //             companyIdentifier: 0x0131, // this is the Cypress identifier, which makes the chip on rpi
    //             companyIdentifier: 0x0009, // this is the Infineon identifier, which makes the chip on rpi
    //             companyIdentifier: 0x004C // this is the Apple identifier, which makes the chip on nrf52
    //         }] },
    //     ],
    // };
    let options = {
        filters: [
            { name: "mpy-uart" },
        ],
    };

    navigator.bluetooth
    .requestDevice(options, acceptAllDevices=true)
    .then((device) => {
        console.log(`Name: ${device.name}`);
        // Do something with the device.
        connected_device = device;
        connected_device.gatt.connect().then((gatt) => {
            // general device stuff @ 0000180a-0000-1000-8000-00805f9b34fb
            gatt.getPrimaryService('6e400001-b5a3-f393-e0a9-e50e24dcca9e').then((serv) => {
                prime_serv = serv;
                prime_serv.getCharacteristic('6e400001-b5a3-f393-e0a9-e50e24dcca9e').then((char) => {
                ble_char = char
                });
            });
        });
        document.getElementById("connection_status").innerText = `Connected`;
        document.getElementById("connection_status").className = `conn-good`;
    })
    .catch((error) => console.error(`Something went wrong. ${error}`));
}

// method for writing to the device
function writeToDevice(message) {
    if (ble_char == null) {
        alert("Device not connected. Please connect to a device first.");
        return;
    }
    ble_char.writeValueWithoutResponce(message);
}
