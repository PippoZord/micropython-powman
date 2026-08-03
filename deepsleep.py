from machine import mem32, idle, Pin
from micropython import const

# POWMAN BASE ADDRESS
POWMAN_BASE = const(0x40100000)

# PASSWORD FOR POWMAN
PASS = const(0x5AFE0000)

# GENERIC REGISTER OFFSET
VREG_LP_ENTRY = const(0x10)
STATE         = const(0x38)
TIMER         = const(0x88)
INTE          = const(0xE4)

# OFFSET FOR TIME REGISTER
SET_TIME_15TO0  = const(0x6C)
SET_TIME_31TO16 = const(0x68)
SET_TIME_47TO32 = const(0x64)
SET_TIME_63TO48 = const(0x60)

# OFFSET FOR ALARM REGISTER
ALARM_TIME_15TO0  = const(0x84)
ALARM_TIME_31TO16 = const(0x80)
ALARM_TIME_47TO32 = const(0x7C)
ALARM_TIME_63TO48 = const(0x78)

# OFFSET FOR READING TIME
READ_TIME_UPPER = const(0x70)
READ_TIME_LOWER = const(0x74)

# OFFSET FOR BOOT REGISTER
BOOT0 = const(0xD0)
BOOT1 = const(0xD4)
BOOT2 = const(0xD8)
BOOT3 = const(0xDC)

# OFFSET POWER CONFIGURATION
DBG_PWRCFG = const(0xA4)

# OFFSET GPIO AWAKE (4 independent GPIO wake-up slots)
PWRUP0 = const(0x8C)
PWRUP1 = const(0x90)
PWRUP2 = const(0x94)
PWRUP3 = const(0x98)

_PWRUP_REGS = (PWRUP0, PWRUP1, PWRUP2, PWRUP3)

# OFFSET WAKEUP REASON
CHIP_RESET        = const(0x2C)
LAST_SWCORE_PWRUP = const(0xA0)

# WAKEUP REASON BITMASK
WAKEUP_CHIP_RESET = const(0x01)
WAKEUP_GPIO0      = const(0x02)
WAKEUP_GPIO1      = const(0x04)
WAKEUP_GPIO2      = const(0x08)
WAKEUP_GPIO3      = const(0x10)
WAKEUP_ALARM      = const(0x40)

# OFFSET PADS
PADS_BANK0_BASE = 0x40038000


# Which optional low-power steps (see the sections below) _powmanPowerOff()
# applies automatically before idle(). Configured once via powmanInit(),
# so callers don't need to build their own beforeSleep callback just to use
# the built-in optimizations. stopXosc is applied immediately here (safe to
# do early); the rest are deferred and applied last, right before idle().
_LOW_POWER = {"rosc": False, "usbPhy": False, "wifiChip": False}


# Initialize POWMAN clock and set absolute time in ms.
# absTimeMs must be > 0.
# lowPowerXosc/Rosc/UsbPhy/WifiChip enable the optional extra power-saving
# steps documented below (stopXosc/stopRosc/isolateUsbPhy/powerDownWifiChip)
# — enabling them here means powmanOff*() applies them automatically,
# without needing a manual beforeSleep callback.
def powmanInit(absTimeMs:int, lowPowerXosc=False, lowPowerRosc=False,
               lowPowerUsbPhy=False, lowPowerWifiChip=False):
    if absTimeMs < 1 :
        raise Exception("absTimeMs must be greater than 0")

    print("Initializing time", absTimeMs)

    # Stop timer
    mem32[POWMAN_BASE + TIMER] = PASS | 0x00

    mem32[POWMAN_BASE + PWRUP0] = PASS | 0x200

    # Set time (64 bit split in 4 x 16 bit)
    mem32[POWMAN_BASE + SET_TIME_15TO0]  = PASS | (absTimeMs & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_31TO16] = PASS | ((absTimeMs >> 16) & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_47TO32] = PASS | ((absTimeMs >> 32) & 0xFFFF)
    mem32[POWMAN_BASE + SET_TIME_63TO48] = PASS | ((absTimeMs >> 48) & 0xFFFF)

    # Start timer
    # RUN + CLEAR + CLEAR ALARM
    mem32[POWMAN_BASE + TIMER] = PASS | 0x46

    # Ignore debugger
    mem32[POWMAN_BASE + DBG_PWRCFG] = PASS | 0x01

    if lowPowerXosc:
        stopXosc()

    _LOW_POWER["rosc"]     = lowPowerRosc
    _LOW_POWER["usbPhy"]   = lowPowerUsbPhy
    _LOW_POWER["wifiChip"] = lowPowerWifiChip


# Return current POWMAN time (64-bit)
def _getCurrentTime():
    while True:
        hi1 = mem32[POWMAN_BASE + READ_TIME_UPPER]
        lo  = mem32[POWMAN_BASE + READ_TIME_LOWER]
        hi2 = mem32[POWMAN_BASE + READ_TIME_UPPER]

        if hi1 == hi2:
            return (hi1 << 32) | lo

# force reboot
def _forceReboot():
    mem32[POWMAN_BASE + BOOT0] = 0
    mem32[POWMAN_BASE + BOOT1] = 0
    mem32[POWMAN_BASE + BOOT2] = 0
    mem32[POWMAN_BASE + BOOT3] = 0


# Applies whichever optional low-power steps were enabled via powmanInit().
# Called last, right before idle() — everything else (arming alarm/GPIOs)
# must already be done, since code after this may run much slower.
def _applyLowPowerConfig():
    if _LOW_POWER["rosc"]:
        stopRosc()
    if _LOW_POWER["usbPhy"]:
        isolateUsbPhy()
    if _LOW_POWER["wifiChip"]:
        powerDownWifiChip()


# Force dormant mode and set reboot enable.
# beforeSleep, if given, is called last (after _applyLowPowerConfig() and
# right before idle()) for any additional custom setup callers want to run.
def _powmanPowerOff(beforeSleep=None):
    # Set low power mode
    mem32[POWMAN_BASE + VREG_LP_ENTRY] = PASS | 0x0004

    _forceReboot()

    # Switch off system
    # Bit 3: SWCORE, Bit 2: XIP, Bit 1: SRAM0, Bit 0: SRAM1
    mem32[POWMAN_BASE + STATE] = PASS | 0x00F0

    _applyLowPowerConfig()

    if beforeSleep:
        beforeSleep()

    # Wait for interrupt / alarm
    idle() # = WFI
    


# Arm the alarm timer to fire after sleepingMs.
# sleepingMs must be > 0
def _armAlarm(sleepingMs: int):
    if sleepingMs < 1 :
        raise Exception("sleepingMs must be greater than 0")

    alarmTime = sleepingMs + _getCurrentTime()
    print("Going to sleep for", sleepingMs, "ms")

    # Stop timer
    mem32[POWMAN_BASE + TIMER] = PASS | 0x00

    # Write alarm time
    mem32[POWMAN_BASE + ALARM_TIME_15TO0]  = PASS | (alarmTime & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_31TO16] = PASS | ((alarmTime >> 16) & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_47TO32] = PASS | ((alarmTime >> 32) & 0xFFFF)
    mem32[POWMAN_BASE + ALARM_TIME_63TO48] = PASS | ((alarmTime >> 48) & 0xFFFF)

    # Start timer + reset alarm bit
    mem32[POWMAN_BASE + TIMER] = PASS | 0x72


# Start dormant mode.
# create and set alarm which trigger awake after sleepingMs.
# sleepingMs must be > 0
def powmanOffForMs(sleepingMs:int, beforeSleep=None):
    # Enable interrupt
    mem32[POWMAN_BASE + INTE] = PASS | 0x02

    _armAlarm(sleepingMs)

    _powmanPowerOff(beforeSleep)


def powmanGetWakeupReason() -> int:
    # HAD_SWCORE_PD (bit 25) is set only when POWMAN explicitly powered down SWCORE
    if mem32[POWMAN_BASE + CHIP_RESET] & (1 << 25):
        return mem32[POWMAN_BASE + LAST_SWCORE_PWRUP]
    return 0  # fresh power-on or software reset

# Arm one PWRUP slot (0-3) to trigger a wake-up on a GPIO transition.
# IMPORTANT: the GPIO must already be at the OPPOSITE level before calling this.
# POWMAN uses level-triggered detection and requires a transition to fire.
# If high=True, GPIO must be LOW before sleep (then goes HIGH → wake).
# If high=False, GPIO must be HIGH before sleep (then goes LOW → wake).
# Sleeping while GPIO is already at the wake level will prevent the chip from waking.
def _armGpioWakeup(gpio: int, high: bool, slot: int):
    if gpio < 0 or gpio > 49:
        raise Exception("gpio must be between 0 and 49")

    if slot not in _PWRUP_REGS:
        raise Exception("slot must be one of PWRUP0, PWRUP1, PWRUP2, PWRUP3")

    GPIO_PAD_CTRL = PADS_BANK0_BASE + ((gpio + 1) * 4)
    # IE (bit6) always on; PUE (bit3) for active-low, PDE (bit2) for active-high
    mem32[GPIO_PAD_CTRL] = 0x48 if not high else 0x44

    direction = 0x80 if high else 0x00  # bit 7: 1=HIGH_RISING, 0=LOW_FALLING
    mem32[POWMAN_BASE + slot] = PASS | 0x40 | direction | gpio


# Force deep sleep until gpio level (True=HIGH, False=LOW).
# slot selects which of the 4 PWRUP registers to use (PWRUP0 by default).
def powmanOffUntilGPIO(gpio: int, high: bool = True, slot=PWRUP0, beforeSleep=None):
    mem32[POWMAN_BASE + INTE] = 0x02

    _armGpioWakeup(gpio, high, slot)

    _powmanPowerOff(beforeSleep)


# Force deep sleep until ANY of up to 4 GPIOs reaches its target level.
# pins: list/tuple of up to 4 (gpio, high) tuples, one per PWRUP slot.
# Use powmanGetWakeupReason() after reboot to tell which one fired
# (WAKEUP_GPIO0..WAKEUP_GPIO3 correspond to pins[0]..pins[3]).
def powmanOffUntilAnyGPIO(pins, beforeSleep=None):
    if not 1 <= len(pins) <= 4:
        raise Exception("pins must contain between 1 and 4 (gpio, high) tuples")

    mem32[POWMAN_BASE + INTE] = 0x02

    for slot, (gpio, high) in zip(_PWRUP_REGS, pins):
        _armGpioWakeup(gpio, high, slot)

    _powmanPowerOff(beforeSleep)


# Force deep sleep until EITHER the timer alarm expires OR any of up to 4 GPIOs
# reaches its target level — whichever happens first wakes the chip.
# sleepingMs must be > 0. pins: list/tuple of up to 4 (gpio, high) tuples.
# Use powmanGetWakeupReason() after reboot to tell which one fired
# (WAKEUP_ALARM for the timer, WAKEUP_GPIO0..WAKEUP_GPIO3 for pins[0]..pins[3]).
def powmanOffForMsOrGPIO(sleepingMs: int, pins, beforeSleep=None):
    if not 1 <= len(pins) <= 4:
        raise Exception("pins must contain between 1 and 4 (gpio, high) tuples")

    mem32[POWMAN_BASE + INTE] = PASS | 0x02

    _armAlarm(sleepingMs)

    for slot, (gpio, high) in zip(_PWRUP_REGS, pins):
        _armGpioWakeup(gpio, high, slot)

    _powmanPowerOff(beforeSleep)


# EXPERIMENTAL: stopping XOSC/ROSC before sleeping (higher risk)
#
# Stops the external crystal (XOSC) and, optionally, the ring oscillator
# (ROSC) before entering POWMAN dormant mode, to save the current they draw
# while running (they live in the always-on domain, so the SWCORE/XIP/SRAM
# power-down above does not touch them). Call stopXosc() and/or stopRosc()
# right before a powmanOff*() call — typically via its beforeSleep hook, so
# arming the alarm/GPIOs happens first while the clock is still fast. There
# is no "wake back up" function: every powmanOff*() wakes via a full chip
# reboot, and the boot ROM reinitializes clocks from scratch, so nothing
# needs restoring here.
#
# The POWMAN alarm timer is unaffected by either of these: per the RP2350
# register docs, POWMAN_TIMER always starts out clocked from its own internal
# LPOSC, and only moves to XOSC if something explicitly sets
# POWMAN_TIMER_USE_XOSC — this library never does, so the alarm keeps
# ticking correctly regardless of what happens to XOSC/ROSC.
#
# RISK: clk_sys/clk_ref must be moved off an oscillator before it is stopped,
# otherwise the system clock disappears and the chip hangs (requires a
# physical reset/reflash to recover). stopRosc() must be called after
# stopXosc() (it assumes clk_ref/clk_sys are no longer sourced from XOSC).
# This has only been tested on Pico 2 (RP2350) with stock boot clock
# configuration.

CLOCKS_BASE = const(0x40010000)
XOSC_BASE   = const(0x40048000)
ROSC_BASE   = const(0x400E8000)

CLK_REF_CTRL     = const(0x30)
CLK_REF_SELECTED = const(0x38)
CLK_SYS_CTRL     = const(0x3C)
CLK_SYS_SELECTED = const(0x44)

XOSC_DORMANT = const(0x08)
ROSC_DORMANT = const(0x10)

OSC_DORMANT_VALUE = const(0x636F6D61)  # "coma"

CLK_REF_SRC_ROSC    = const(0x0)
CLK_REF_SRC_LPOSC   = const(0x3)
CLK_SYS_SRC_CLK_REF = const(0x0)

# one-hot: bit N set once the glitchless mux has actually settled on source N
CLK_REF_SELECTED_ROSC    = const(1 << 0)
CLK_REF_SELECTED_LPOSC   = const(1 << 3)
CLK_SYS_SELECTED_CLK_REF = const(1 << 0)


# Move clk_ref and clk_sys off XOSC/PLL onto the ring oscillator (ROSC), then
# stop XOSC. Only call this right before going to sleep.
# ROSC is not touched here: it's enabled by default at power-up, and blindly
# writing its control register would also clobber its FREQ_RANGE field.
def stopXosc():
    # clk_ref: switch away from XOSC onto ROSC. The glitchless mux doesn't
    # switch instantly, so wait for CLK_REF_SELECTED to confirm it before
    # relying on it downstream (same pattern the pico-sdk's clock_configure()
    # uses).
    mem32[CLOCKS_BASE + CLK_REF_CTRL] = CLK_REF_SRC_ROSC
    while not (mem32[CLOCKS_BASE + CLK_REF_SELECTED] & CLK_REF_SELECTED_ROSC):
        pass

    # clk_sys: switch away from the PLL/aux path onto clk_ref (now ROSC-backed).
    mem32[CLOCKS_BASE + CLK_SYS_CTRL] = CLK_SYS_SRC_CLK_REF
    while not (mem32[CLOCKS_BASE + CLK_SYS_SELECTED] & CLK_SYS_SELECTED_CLK_REF):
        pass

    # Nothing left depends on XOSC now — stop it.
    mem32[XOSC_BASE + XOSC_DORMANT] = OSC_DORMANT_VALUE


# Move clk_ref (and, transitively, clk_sys) off ROSC onto POWMAN's own
# low-power oscillator (LPOSC, always on), then stop ROSC.
# Call this AFTER stopXosc() — it assumes clk_ref is currently on ROSC.
def stopRosc():
    mem32[CLOCKS_BASE + CLK_REF_CTRL] = CLK_REF_SRC_LPOSC
    while not (mem32[CLOCKS_BASE + CLK_REF_SELECTED] & CLK_REF_SELECTED_LPOSC):
        pass

    # Nothing left depends on ROSC now — stop it.
    mem32[ROSC_BASE + ROSC_DORMANT] = OSC_DORMANT_VALUE


# USB PHY isolation (low risk)
#
# Re-isolates the USB PHY before entering POWMAN dormant mode, matching the
# methodology the RP2350 datasheet itself uses for its own documented
# low-power current figures (section 14.9.7.2): MAIN_CTRL.PHY_ISO=1 with the
# DP/DM pulldowns enabled. PHY_ISO defaults to 1 (isolated) at reset and gets
# cleared by MicroPython's own USB init to run the serial console — this
# just puts it back before sleeping, since the reboot on wake reinitializes
# USB from scratch regardless.
#
# Lower risk than stopXosc()/stopRosc(): this only isolates a peripheral, it
# does not touch clk_sys/clk_ref, so there is no clock-hang risk. Call this
# right before going to sleep (e.g. as part of a powmanOff*() beforeSleep
# hook) — any USB activity (like the serial console) still in flight at that
# point will just disconnect a little earlier than the reboot would do anyway.

USBCTRL_REGS_BASE = const(0x50110000)

MAIN_CTRL = const(0x40)
SIE_CTRL  = const(0x4C)

MAIN_CTRL_PHY_ISO    = const(1 << 2)
SIE_CTRL_PULLDOWN_EN = const(1 << 15)


def isolateUsbPhy():
    mem32[USBCTRL_REGS_BASE + MAIN_CTRL] |= MAIN_CTRL_PHY_ISO
    mem32[USBCTRL_REGS_BASE + SIE_CTRL]  |= SIE_CTRL_PULLDOWN_EN


# CYW43439 wireless chip power-down (Pico 2 W only, low risk)
CYW43_WL_REG_ON = const(23)


def powerDownWifiChip():
    Pin(CYW43_WL_REG_ON, Pin.OUT, value=0)
