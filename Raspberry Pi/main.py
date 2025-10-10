from machine import Pin, SPI
import time
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral

# Create a Bluetooth Low Energy (BLE) object
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble)

led = Pin("LED", Pin.OUT)
led_state = 0

# SPI0 setup
spi = SPI(0, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19), miso=Pin(16))
cs = Pin(17, Pin.OUT)
io_update = Pin(20, Pin.OUT)

cs.value(1)
io_update.value(0)

# AD9959 Constants
# Adjust these based on your system clock frequency
SYSTEM_CLOCK = 50_000_000  # 50 MHz (adjust to your actual clock)

def io_update_pulse():
    io_update.value(1)
    time.sleep_us(1)
    io_update.value(0)

def write_reg(addr, data_bytes):
    instr = addr & 0x1F  # write operation
    tx = bytearray([instr] + data_bytes)
    cs.value(0)
    spi.write(tx)
    cs.value(1)
    io_update_pulse()
    print("Sent:", [hex(x) for x in tx])

def frequency_to_ftw(frequency):
    """Convert frequency in Hz to Frequency Tuning Word (FTW) for AD9959"""
    # FTW = (frequency / system_clock) * 2^32
    ftw = int((frequency / SYSTEM_CLOCK) * (2**32))
    return ftw

def set_frequency(channel, frequency):
    """Set the frequency for a specific channel (0-3)"""
    ftw = frequency_to_ftw(frequency)
    
    # Convert FTW to 4 bytes (big-endian)
    ftw_bytes = [
        (ftw >> 24) & 0xFF,
        (ftw >> 16) & 0xFF,
        (ftw >> 8) & 0xFF,
        ftw & 0xFF
    ]
    
    # Channel Frequency Tuning Word register addresses
    # Channel 0: 0x04, Channel 1: 0x05, Channel 2: 0x06, Channel 3: 0x07
    ftw_addr = 0x04 + channel
    
    print(f"Setting channel {channel} to {frequency} Hz")
    print(f"FTW: {hex(ftw)} -> {[hex(x) for x in ftw_bytes]}")
    
    write_reg(ftw_addr, ftw_bytes)

def parse_frequency_data(data):
    """Parse incoming BLE data for frequency commands"""
    try:
        # Convert bytes to string and strip whitespace
        data_str = data.decode('utf-8').strip()
        print(f"Parsed data: {data_str}")
        
        # Handle single frequency: "1000"
        if ',' not in data_str:
            freq = float(data_str)
            set_frequency(0, freq)  # Set channel 0
            return
        
        # Handle two frequencies: "1000,2000"
        freqs = data_str.split(',')
        if len(freqs) >= 2:
            freq1 = float(freqs[0].strip())
            freq2 = float(freqs[1].strip())
            set_frequency(0, freq1)
            set_frequency(1, freq2)
            return
            
    except (ValueError, UnicodeDecodeError) as e:
        print(f"Error parsing data: {e}")

def on_rx(data):
    """Callback function for incoming BLE data"""
    print("Data received: ", data)
    
    global led_state
    
    # Handle single-byte commands
    if data == b'T':
        led.value(not led_state)
        led_state = 1 - led_state
        print("Light toggled")
        return
    
    if data == b'W':
        write_reg(0x01, [0x5A, 0x3A, 0xD0])
        return
    
    # Handle frequency data (e.g., "1000\n" or "1000,2000\n")
    parse_frequency_data(data)

# Start an infinite loop
print("BLE Peripheral started, waiting for connections...")
while True:
    if sp.is_connected():
        sp.on_write(on_rx)
    time.sleep(0.1)