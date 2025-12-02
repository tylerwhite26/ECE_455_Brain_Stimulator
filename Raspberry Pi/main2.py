from machine import Pin, SPI
import time
import bluetooth
from ble_simple_peripheral import BLESimplePeripheral

# Create a Bluetooth Low Energy (BLE) object
ble = bluetooth.BLE()
sp = BLESimplePeripheral(ble)
led = Pin("LED", Pin.OUT)
led_state = 0

# SPI0 setup - Shared by all four AD9833 chips
# AD9833 datasheet shows CPOL=1, CPHA=0 (SPI Mode 2)
# SCLK can be up to 40 MHz, using 1 MHz for reliability
#spi = SPI(0, baudrate=1_000_000, polarity=1, phase=0,
#          sck=Pin(18), mosi=Pin(19), miso=Pin(16))

spi = SPIspi = SPI(1, baudrate=1_000_000, polarity=1, phase=1,
             sck=Pin(14), mosi=Pin(15), miso=Pin(12))

# FSYNC pins for each AD9833 (active low chip select)
# Each chip needs its own FSYNC pin
fsync_pins = [
    Pin(17, Pin.OUT),  # AD9833 #0
    Pin(20, Pin.OUT),  # AD9833 #1
    Pin(21, Pin.OUT),  # AD9833 #2
    Pin(22, Pin.OUT)   # AD9833 #3
]

# Initialize all FSYNC pins to idle high
for pin in fsync_pins:
    pin.value(1)

# AD9833 Constants
SYSTEM_CLOCK = 25_000_000  # 25 MHz typical reference clock
# Adjust this to match your actual MCLK frequency

# AD9833 Control Register Bits (when D15=0, D14=0)
B28 = 0x2000      # 0x2000 = Bit 13: 28-bit frequency write mode
HLB = 0x1000      # 0x1000 = Bit 12: Half-load bit (MSB/LSB select)
FSELECT = 0x0800  # 0x0800 = Bit 11: Frequency register select
PSELECT = 0x0400  # 0x0400 = Bit 10: Phase register select
RESET = 0x0100    # 0x0100 = Bit 8: Reset
SLEEP1 = 0x0080   # 0x0080 = Bit 7: Power down MCLK
SLEEP12 = 0x0040  # 0x0040 = Bit 6: Power down DAC
OPBITEN = 0x0020  # 0x0020 = Bit 5: Output MSB of DAC data
DIV2 = 0x0008     # 0x0008 = Bit 3: Divide MSB by 2
MODE = 0x0002     # 0x0002 = Bit 1: Triangle wave output

# Frequency Register Address Bits
FREQ0_ADDR = 0x4000  # D15=0, D14=1
FREQ1_ADDR = 0x8000  # D15=1, D14=0

# Phase Register Address Bits
PHASE0_ADDR = 0xC000  # D15=1, D14=1, D13=0
PHASE1_ADDR = 0xE000  # D15=1, D14=1, D13=1

def write_word(channel, data):
    """
    Write 16-bit word to specified AD9833 channel
    channel: 0-3 (which AD9833 chip to write to)
    """
    if channel < 0 or channel >= len(fsync_pins):
        print(f"Error: Invalid channel {channel}")
        return
    
    tx = bytearray([
        (data >> 8) & 0xFF,
        data & 0xFF
    ])
    print(tx)
    fsync_pins[channel].value(0)  # FSYNC low to enable writing
    spi.write(tx)
    fsync_pins[channel].value(1)  # FSYNC high to latch data
    time.sleep_us(1)
    print(f"Ch{channel} Sent: {hex(data)}")

def frequency_to_ftw(frequency):
    """Convert frequency in Hz to Frequency Tuning Word (FTW) for AD9833"""
    # FTW = (frequency * 2^28) / MCLK
    ftw = int((frequency * (2**28)) / SYSTEM_CLOCK)
    return ftw & 0x0FFFFFFF  # Ensure 28-bit value

def test():
    write_word(0, 0x2108)
    write_word(0, 0x2008)
    write_word(0, 0x5893)
    write_word(0, 0x4010)

def init_ad9833(channel):
    """
    Initialize specified AD9833 channel with proper startup sequence
    channel: 0-3 (which AD9833 chip to initialize)
    """
    print(f"Initializing AD9833 channel {channel}...")
    
    # Step 1: Apply reset
    write_word(channel, RESET)
    time.sleep_ms(1)
    
    # Step 2: Configure for 28-bit frequency writes (B28=1)
    write_word(channel, B28)
    
    # Step 3: Initialize frequency registers to 0 (optional but recommended)
    write_word(channel, FREQ0_ADDR | 0x0000)  # FREQ0 LSBs
    write_word(channel, FREQ0_ADDR | 0x0000)  # FREQ0 MSBs
    
    # Step 4: Initialize phase register to 0
    write_word(channel, PHASE0_ADDR | 0x0000)
    
    # Step 5: Clear reset to start output
    write_word(channel, 0x0000)
    
    print(f"AD9833 channel {channel} initialized")

def init_all_ad9833():
    """Initialize all four AD9833 chips"""
    for ch in range(4):
        init_ad9833(ch)
        time.sleep_ms(10)

def set_frequency(channel, frequency, freq_reg=0):
    """
    Set the frequency for specified AD9833 channel
    channel: 0-3 (which AD9833 chip)
    frequency: Frequency in Hz
    freq_reg: 0 for FREQ0, 1 for FREQ1
    
    Output frequency = (MCLK × FREQREG) / 2^28
    """
    if channel < 0 or channel >= len(fsync_pins):
        print(f"Error: Invalid channel {channel}")
        return
    
    ftw = frequency_to_ftw(frequency)
    
    # Split 28-bit FTW into two 14-bit words
    lsb = ftw & 0x3FFF          # Lower 14 bits
    msb = (ftw >> 14) & 0x3FFF  # Upper 14 bits
    
    print(f"Ch{channel}: Setting frequency to {frequency} Hz")
    print(f"FTW: {hex(ftw)} (LSB: {hex(lsb)}, MSB: {hex(msb)})")
    
    # Select frequency register base address
    reg_base = FREQ0_ADDR if freq_reg == 0 else FREQ1_ADDR
    
    # Write LSBs first, then MSBs (per datasheet Table 9)
    write_word(channel, reg_base | lsb)
    write_word(channel, reg_base | msb)
    
    # Exit reset mode to apply changes
    write_word(channel, B28)

def set_all_frequencies(frequencies):
    """
    Set frequencies for all four channels
    frequencies: List of 4 frequencies in Hz [freq0, freq1, freq2, freq3]
    """
    if len(frequencies) != 4:
        print("Error: Need exactly 4 frequencies")
        return
    
    for ch, freq in enumerate(frequencies):
        if freq > 0:
            set_frequency(ch, freq)
        time.sleep_ms(5)

def set_phase(channel, phase_deg, phase_reg=0):
    """
    Set the phase offset in degrees (0-360)
    channel: 0-3 (which AD9833 chip)
    phase_deg: Phase in degrees
    phase_reg: 0 for PHASE0, 1 for PHASE1
    
    Phase resolution is 2π/4096 = 0.0879 degrees
    """
    if channel < 0 or channel >= len(fsync_pins):
        print(f"Error: Invalid channel {channel}")
        return
    
    # Convert degrees to 12-bit phase value (0-4095)
    phase_val = int((phase_deg / 360.0) * 4096) & 0x0FFF
    
    reg_base = PHASE0_ADDR if phase_reg == 0 else PHASE1_ADDR
    write_word(channel, reg_base | phase_val)
    print(f"Ch{channel}: Phase set to {phase_deg}° (value: {phase_val})")

def set_output_mode(channel, mode='sine'):
    """
    Set output waveform type for specified channel
    channel: 0-3 (which AD9833 chip)
    mode: 'sine', 'triangle', 'square', or 'square_div2'
    """
    if channel < 0 or channel >= len(fsync_pins):
        print(f"Error: Invalid channel {channel}")
        return
    
    if mode == 'triangle':
        # Triangle: MODE=1, OPBITEN=0
        write_word(channel, B28 | MODE)
    elif mode == 'square':
        # Square wave (MSB of DAC): OPBITEN=1, DIV2=1
        write_word(channel, B28 | OPBITEN | DIV2)
    elif mode == 'square_div2':
        # Square wave divided by 2: OPBITEN=1, DIV2=0
        write_word(channel, B28 | OPBITEN)
    else:  # sine
        # Sine: MODE=0, OPBITEN=0
        write_word(channel, B28)
    
    print(f"Ch{channel}: Output mode set to {mode}")

def sleep_mode(channel, sleep_dac=False, sleep_mclk=False):
    """
    Put specified AD9833 channel into sleep mode to save power
    channel: 0-3 (which AD9833 chip), or -1 for all channels
    sleep_dac: Power down the DAC
    sleep_mclk: Disable internal MCLK (NCO stops)
    """
    control = B28
    if sleep_dac:
        control |= SLEEP12
    if sleep_mclk:
        control |= SLEEP1
    
    if channel == -1:
        # Apply to all channels
        for ch in range(4):
            write_word(ch, control)
        print(f"All channels sleep: DAC={'off' if sleep_dac else 'on'}, MCLK={'off' if sleep_mclk else 'on'}")
    else:
        if channel >= 0 and channel < len(fsync_pins):
            write_word(channel, control)
            print(f"Ch{channel} sleep: DAC={'off' if sleep_dac else 'on'}, MCLK={'off' if sleep_mclk else 'on'}")

def parse_frequency_data(data):
    """
    Parse incoming BLE data for frequency commands
    Format: "freq0,freq1,freq2,freq3" or "ch:freq" or "ch:freq,phase"
    Examples:
    - "1000,2000,3000,4000" - Set all four channels
    - "0:5000" - Set channel 0 to 5000 Hz
    - "1:10000,90" - Set channel 1 to 10000 Hz with 90° phase
    """
    try:
        # Convert bytes to string and strip whitespace
        data_str = data.decode('utf-8').strip()
        print(f"Parsed data: {data_str}")
        
        # Check if this is a channel-specific command (contains ":")
        if ':' in data_str:
            # Format: "ch:freq" or "ch:freq,phase"
            parts = data_str.split(':')
            channel = int(parts[0])
            
            if ',' in parts[1]:
                # Frequency and phase
                freq_phase = parts[1].split(',')
                freq = float(freq_phase[0].strip())
                phase = float(freq_phase[1].strip())
                set_frequency(channel, freq)
                set_phase(channel, phase)
            else:
                # Frequency only
                freq = float(parts[1].strip())
                set_frequency(channel, freq)
        else:
            # Format: "freq0,freq1,freq2,freq3" - set all channels
            freqs_str = data_str.split(',')
            if len(freqs_str) == 4:
                freqs = [float(f.strip()) for f in freqs_str]
                set_all_frequencies(freqs)
            elif len(freqs_str) == 1:
                # Single frequency - apply to all channels
                freq = float(freqs_str[0].strip())
                set_all_frequencies([freq, freq, freq, freq])
            
    except (ValueError, UnicodeDecodeError, IndexError) as e:
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
    
    if data == b'R':
        # Reset and reinitialize all channels
        init_all_ad9833()
        return
    
    if data.startswith(b'S'):
        # Set sine wave output
        # 'S' = all channels, 'S0'-'S3' = specific channel
        if len(data) == 1:
            for ch in range(4):
                set_output_mode(ch, 'sine')
        else:
            ch = int(chr(data[1]))
            set_output_mode(ch, 'sine')
        return
    
    if data.startswith(b'W'):
        # Set triangle wave output
        if len(data) == 1:
            for ch in range(4):
                set_output_mode(ch, 'triangle')
        else:
            ch = int(chr(data[1]))
            set_output_mode(ch, 'triangle')
        return
    
    if data.startswith(b'Q'):
        # Set square wave output
        if len(data) == 1:
            for ch in range(4):
                set_output_mode(ch, 'square')
        else:
            ch = int(chr(data[1]))
            set_output_mode(ch, 'square')
        return
    
    if data == b'P':
        # Power save mode - sleep all channels
        sleep_mode(-1, sleep_dac=True, sleep_mclk=True)
        return
    
    if data == b'U':
        # Wake up all channels from sleep
        sleep_mode(-1, sleep_dac=False, sleep_mclk=False)
        return
    
    # Handle frequency data
    parse_frequency_data("1000,2000,3000,4000")

# Initialize all four AD9833 chips
print("Initializing four AD9833 DDS chips...")
print(f"FSYNC pins: GPIO 17, 20, 21, 22")
test()
print(f"System clock: {SYSTEM_CLOCK} Hz")
print(f"Frequency resolution: {SYSTEM_CLOCK / (2**28):.4f} Hz")
print("\n=== BLE Command Reference ===")
print("T - Toggle LED")
print("R - Reset all channels")
print("S/S0-S3 - Sine wave (all/specific channel)")
print("W/W0-W3 - Triangle wave (all/specific channel)")
print("Q/Q0-Q3 - Square wave (all/specific channel)")
print("P - Sleep all channels")
print("U - Wake all channels")
print("1000,2000,3000,4000 - Set all four frequencies")
print("0:5000 - Set channel 0 to 5000 Hz")
print("1:10000,90 - Set channel 1 to 10kHz, 90° phase")
print("=============================\n")

# Start an infinite loop
# print("BLE Peripheral started, waiting for connections...")
# Test sequence after fixing the above functions
print("=== AD9833 Sine Wave Test ===")

# Initialize all chips
init_all_ad9833()
time.sleep_ms(100)

# Set all channels to 1kHz sine wave
print("\nSetting 1kHz on all channels...")
for ch in range(4):
    set_frequency(ch, 1000)
    set_output_mode(ch, 'sine')
    time.sleep_ms(50)

print("\nTest complete! Check VOUT pins with oscilloscope.")
print("Expected: ~0.6V peak-to-peak sine wave at 1kHz")
    #time.sleep(0.1)