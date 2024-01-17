from playsound import playsound

from constants import SL_UPDATED_SUCCESS, STOP_LOSS_UPDATED_SUCCESS


def play_audio(file_path):
    try:
        print("Sound Play disabled")
        playsound(file_path)
    except Exception as e:
        print("Error While playing alert")


play_audio(STOP_LOSS_UPDATED_SUCCESS)
