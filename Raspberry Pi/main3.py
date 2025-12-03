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
    
def test(): # write to DDS
    write_word(0, 0x2108)
    write_word(0, 0x2008)
    write_word(0, 0x5893)
    write_word(0, 0x4010)

#programmable resistors Pins
pins = [
    Pin(2, Pin.OUT),
    Pin(3, Pin.OUT)
    ]

def increment(n):
    pins[1].value(1)
    pins[0].value(0) # CS low
    
    for i in range(n):
        pins[1].value(0)
        pins[1].value(1)
        
    pins[0].value(1) # CS high
    
def decrement(n):
    pins[1].value(0)
    pins[0].value(0) # CS low
    
    for i in range(n):
        pins[1].value(1)
        pins[1].value(0)
    
    pins[0].value(1) # CS high


pins[0].value(1) #cs high
decrement(64) #reset prorgammable resistor to 00h
test() # DDS
