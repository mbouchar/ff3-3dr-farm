#!/usr/bin/env python

from pyautogui import ImageNotFoundException
import subprocess
import pyautogui
import psutil
import time
import os
#import dbus

FF3_3DR_APP_ID = "239120"

def pressFix(keys, interval = 0.1):
    if not isinstance(keys, list):
        keys = [keys]
    
    for key in keys:
        with pyautogui.hold(key):
            time.sleep(interval)

def detection_application(nom_application):
    for p in psutil.process_iter():
        if p.name() == nom_application:
            return True

    return False

def attendre_image(nom_image, boucler = True, temps_attente = 1.0, keys = None, debug = True, **kwargs):
    while True:
        try:
            if debug:
                print(f"Détection de l'image {nom_image}")
            res = pyautogui.locateOnScreen(nom_image, **kwargs)
            return res
        except ImageNotFoundException:
            if debug:
                print(f"L'image {nom_image} n'a pas été trouvé")
            if keys is not None:
                pressFix(keys)
            if boucler:
                print("On attend et on réesaye la détection")
                time.sleep(temps_attente)
            else:
                return None

###

def steam_is_running():
    return detection_application("steam")

def demarrer_steam():
    env = os.environ
    env["STEAM_FORCE_DESKTOPUI_SCALING"] = "1.25"
    subprocess.Popen("/usr/games/steam", env = env)

def ff3_3dr_launcher_is_running():
    return detection_application("FF3_Launcher.ex")

def demarrer_ff3_3dr_launcher():
    subprocess.Popen(["/usr/games/steam", f"steam://rungameid/{FF3_3DR_APP_ID}"])

def ff3_3dr_is_running():
    return detection_application("FF3_Win32")

def detection_launcher(demarrer_jeu = False):
    res = attendre_image("screenshots/ff3/launcher/jouer.png")
    if demarrer_jeu:
        print("Démarrage du jeu Final Fantasy III (3D Remake)")
        pyautogui.click(pyautogui.center(res))

def detection_menu_principal(attendre = True):
    res = attendre_image("screenshots/ff3/menu.png", keys = ["enter"], boucler = False)
    return res is not None

def demarrer_partie():
    print("Démarrage de la partie")
    pressFix(["enter", "enter"])

def detection_in_game(attendre = True, keys = None):
    res = attendre_image("screenshots/ff3/in-game.png", boucler = attendre, keys = keys)
    return res is not None

def est_en_combat(attendre = True):
    res = attendre_image("screenshots/ff3/en-combat.png", boucler = attendre)
    return res is not None

def valider_attaque_automatique(activer = True):
    res = attendre_image("screenshots/ff3/combat-auto.png", boucler = False, grayscale = True, confidence = 0.9)
    if res is None and activer:
        print("Activation du combat automatique")
        pressFix("a")
    else:
        print("Le combat automatique est déjà activé")

def attendre_fin_combat(attendre = True):
    while attendre_image("screenshots/ff3/en-combat.png", boucler = False) is None:
        time.sleep(0.5)
    return True

def lvl_up():
    valider_attaque_automatique(activer = True)
    attendre_fin_combat()

def lvl_jobs():
    pass

def main_loop(script):
    while True:
        while True:
            print("Se déplacer pour démarrer un combat")
            with pyautogui.hold("left"):
                if est_en_combat(attendre = False):
                    break
                time.sleep(0.5)
            with pyautogui.hold("right"):
                if est_en_combat(attendre = False):
                    break
                time.sleep(0.5)
        
        print("Combat démarré")
        script()
        print("Combat terminé!")
        detection_in_game(keys = ["enter", "enter"])

if __name__ == "__main__":
    try:
        from datetime import datetime
        start = datetime.now()

        if not ff3_3dr_is_running():
            if not ff3_3dr_launcher_is_running():
                if not steam_is_running():
                    print("Steam n'est pas en cours d'exécution, on le démarre")
                    demarrer_steam()
                else:
                    print("Steam est déjà démarré")

                print("Démarrage de FF3 3D Remake")
                demarrer_ff3_3dr_launcher()

            detection_launcher(demarrer_jeu = True)
        else:
            print("Le jeu FF3 3D Remake est déjà démarré")

        while not detection_in_game(attendre = False):
            if detection_menu_principal(attendre = False):
                demarrer_partie()

        print("Setup initial terminé!!!")
        main_loop(script = lvl_up)

        end = datetime.now()
        print(end - start)
    except KeyboardInterrupt:
        pass
