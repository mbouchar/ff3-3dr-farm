#!/usr/bin/env python

from pyautogui import ImageNotFoundException
from enum import Enum
import subprocess
import pyautogui
import psutil
import time
import os
import dbus

FF3_3DR_APP_ID = "239120"

class ScreenSaver(object):
    def __init__(self):
        self.__bus_ = dbus.SessionBus()
        self.__saver_object_ = self.__bus_.get_object('org.freedesktop.ScreenSaver', '/ScreenSaver')
        self.__saver_interface_ = dbus.Interface(self.__saver_object_, dbus_interface = 'org.freedesktop.ScreenSaver')
        self.__cookie_ = None

    def disable(self):
        if self.__cookie_ is None:
            print("Désactivation du screensaver")
            self.__cookie_ = self.__saver_interface_.Inhibit("ff33dr_automater", "Farming")

    def enable(self):
        if self.__cookie_ is not None:
            print("Réactivation du screensaver")
            self.__saver_interface_.UnInhibit(self.__cookie_)
            self.__cookie_ = None

class Direction(Enum):
    gauche_droite = 0
    haut_bas = 1

def pressFix(keys, interval = 0.1):
    if not isinstance(keys, list):
        keys = [keys]
    
    for key in keys:
        with pyautogui.hold(key):
            time.sleep(interval)

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

def detection_application(nom_application):
    for p in psutil.process_iter():
        if p.name() == nom_application:
            return True

    return False

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

###

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

def detection_in_game(attendre = True, keys = None, temps_attente = 0.5):
    res = attendre_image("screenshots/ff3/in-game.png", boucler = attendre, keys = keys, temps_attente = temps_attente)
    return res is not None

def est_en_combat(attendre = True):
    res = attendre_image("screenshots/ff3/en-combat.png", boucler = attendre)
    return res is not None

def valider_attaque_automatique(activer = True):
    res = attendre_image("screenshots/ff3/combat-auto.png", boucler = False, grayscale = True, confidence = 0.9)
    if res is None:
        if activer:
            print("Activation du combat automatique")
            pressFix("a")
        else:
            print("Le combat automatique n'est pas activé")
            return False
    else:
        print("Le combat automatique est déjà activé")

    return True

def bloquer():
    pressFix(["down", "down", "enter"], interval = 0.2)
    time.sleep(0.4)

def attaquer():
    pressFix(["enter", "enter"], interval = 0.2)
    time.sleep(0.4)

def attendre_prochain_tour(attendre = True):
    while attendre_image("screenshots/ff3/debut-tour.png", boucler = False) is None:
        if attendre:
            time.sleep(0.2)
        else:
            return False
    return True

def attendre_fin_combat(attendre = True):
    while attendre_image("screenshots/ff3/en-combat.png", boucler = False) is None:
        if attendre:
            time.sleep(0.2)
        else:
            return False
    return True

def lvl_up():
    valider_attaque_automatique()
    attendre_fin_combat()

def lvl_jobs(combat_rapide = True, nombre_garde = 6):    
    # Désactiver l'attaque automatique
    if valider_attaque_automatique(activer = False):
        print("Désactivation de l'attaque automatique")
        pressFix("a")

    if combat_rapide:
        print("Blocage initial")
        for j in range(4):
            print(f"Bloquer avec le personnage {j}")
            bloquer()
        print(f"Démarrage de l'attaque automatique pour {nombre_garde} tours")
        # Activer l'attaque automatique
        valider_attaque_automatique()
        # Ça prend environs 5 secondes par tour
        time.sleep(5 * nombre_garde)
        print("Désactivation de l'attaque automatique")
        pressFix("a")
    else:
        # Bloquer 6 fois pour monter de niveau
        for i in range(nombre_garde):
            print(f"Tour de combat #{i}")
            print("Attente du prochain tour de combat")
            attendre_prochain_tour()
            print("Le prochain tour de combat est démarré")
            for j in range(4):
                print(f"Bloquer avec le personnage {j}")
                bloquer()

    attendre_prochain_tour()
    for i in range(4):
        print(f"Attaque avec le personnage {i}")
        attaquer()
    
    attendre_fin_combat()

def main_loop(script = lvl_up, direction = Direction.gauche_droite, delai_deplacement = 0.5):
    if direction == Direction.gauche_droite:
        direction1 = "left"
        direction2 = "right"
    else:
        direction1 = "up"
        direction2 = "down"

    while True:
        try:
            while True:
                print("Se déplacer pour démarrer un combat")
                with pyautogui.hold(direction1):
                    if est_en_combat(attendre = False):
                        break
                    time.sleep(delai_deplacement)
                with pyautogui.hold(direction2):
                    if est_en_combat(attendre = False):
                        break
                    time.sleep(delai_deplacement)
            
            print("Combat démarré")
            script()
            print("Combat terminé!")
            detection_in_game(keys = ["enter", "enter", "enter"], temps_attente = 0.2)
        except pyautogui.FailSafeException:
            pass

if __name__ == "__main__":
    screenSaver = ScreenSaver()
    try:
        from datetime import datetime
        start = datetime.now()

        screenSaver.disable()

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

        print("Configuration initiale terminé!!!")
        #main_loop(script = lvl_up)
        main_loop(script = lvl_jobs, delai_deplacement = 0)
    except KeyboardInterrupt:
        pass
    finally:
        end = datetime.now()
        print(end - start)

        screenSaver.enable()
