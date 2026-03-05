



def percent_to_gain(percent):
    # percent: 0-100
    # return: -60 to 20 dB
    return (percent * 0.8) - 60


def gain_to_percent(gain):
    # gain: -60 to 20 dB
    # return: 0-100
    return int((gain + 60) / 0.8)




import math

def percent_to_gain_log(percent):
    # percent: 0-100
    # return: -60 to 20 dB (логарифмическая шкала)
    if percent <= 0:
        return -60
    return 20 * math.log10(percent / 100 * 1000) - 60





print(percent_to_gain(100))