from config import VOLUME


def percent_to_gain(percent: int) -> float:
    """ Проценты переводит в GAIN
        percent: 0-100
        return: -60 to 20 dB"""

    if percent > 100 and percent < 0:
        print("Error: Громкость от 0 - 100%")
        percent = VOLUME

    return int((percent * 0.8) - 60)
               


def gain_to_percent(gain) -> int:
    """ dB переводит в проценты от 0 - 100%
        gain: -60 to 20 dB
        return: 0-100 """
    return int((gain + 60) / 0.8)




# import math

# def percent_to_gain_log(percent):
#     # percent: 0-100
#     # return: -60 to 20 dB (логарифмическая шкала)
#     if percent <= 0:
#         return -60
#     return 20 * math.log10(percent / 100 * 1000) - 60





print(percent_to_gain(100))
#print(type(percent_to_gain(100)))