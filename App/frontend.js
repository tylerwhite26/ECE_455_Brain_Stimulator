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



function startBluetooth() {
    var can_support = navigator.bluetooth.getAvailability();
    if (!can_support) {
        alert("Web Bluetooth is not supported on this browser.");
        return;
    }

    // from mozilla web docs
    let options = {
        filters: [
            { manufacturerData: [{
                companyIdentifier: 0x00A050
            }] },
        ],
    };

    navigator.bluetooth
    .requestDevice(options)
    .then((device) => {
        console.log(`Name: ${device.name}`);
        // Do something with the device.
    })
    .catch((error) => console.error(`Something went wrong. ${error}`));
}
