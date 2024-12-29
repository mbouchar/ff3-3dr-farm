#!/usr/bin/env python

from pyautogui import ImageNotFoundException
from enum import Enum
import subprocess
import pyautogui
import psutil
import shutil
import time
import sys
import os
import dbus

SUPPORTED_SESSIONS = ["KDE"]
STEAM_EXE = shutil.which("steam")
FF3_3DR_APP_ID = "239120"
RATIO = None

###
# Utilitaires
##############

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

def get_scaling_ratio(debug = True):
    session = None
    if sys.platform == "linux":
        session = os.environ["XDG_SESSION_DESKTOP"]

    RATIO = None
    match session:
        case "KDE":
            from PyQt5.QtGui import QGuiApplication
            app = QGuiApplication(sys.argv)
            screen = app.primaryScreen()
            RATIO = screen.devicePixelRatio()
        case _:
            raise NotImplementedError(f"La session '{session}' n'est pas supportée")

    if debug:
        print(f"Le ratio de l'écran est: {RATIO}")

    return RATIO

def get_scaled_filename(nom_image):
    if RATIO is not None:
        nom_image, ext = os.path.splitext(nom_image)
        nom_image = f"{nom_image}-{RATIO}{ext}"

    return nom_image

def detection_application(nom_application):
    for p in psutil.process_iter():
        if p.name() == nom_application:
            return True

    return False

def steam_is_running():
    return detection_application("steam")

def demarrer_steam(ratio = 1.0):
    env = os.environ
    env["STEAM_FORCE_DESKTOPUI_SCALING"] = str(ratio)
    subprocess.Popen(STEAM_EXE, env = env)

def attendre_image(nom_image, boucler = True, temps_attente = 1.0, keys = None, debug = True, **kwargs):
    nom_image = get_scaled_filename(nom_image)
    while True:
        try:
            if debug:
                print(f"Détection de l'image {nom_image}")
            sc = screenshotFix()
            res = pyautogui.locate(nom_image, sc, **kwargs)
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
# Correctifs de problèmes de la librairie pyautogui
####################################################

from tempfile import NamedTemporaryFile
from PIL import Image
import pyscreenshot as ImageGrab
def screenshotFix(imageFilename=None, region=None):
    if imageFilename is None:
        tmpFile = NamedTemporaryFile(suffix = ".png", delete_on_close = False)
        tmpFile.close()
        tmpFilename = tmpFile.name
    else:
        tmpFilename = imageFilename

    if region is not None:
        im = ImageGrab.grab(bbox=(region[0], region[1], region[2] + region[0], region[3] + region[1]))
    else:
        im = ImageGrab.grab()
    im.save(tmpFilename)

    im = Image.open(tmpFilename)

    if region is not None:
        assert len(region) == 4, 'region argument must be a tuple of four ints'
        assert isinstance(region[0], int) and isinstance(region[1], int) and isinstance(region[2], int) and isinstance(region[3], int), 'region argument must be a tuple of four ints'
        im = im.crop((region[0], region[1], region[2] + region[0], region[3] + region[1]))
        os.unlink(tmpFilename)  # delete image of entire screen to save cropped version
        im.save(tmpFilename)
    else:
        # force loading before unlinking, Image.open() is lazy
        im.load()

    if imageFilename is None:
        os.unlink(tmpFilename)
    return im

def pressFix(keys, interval = 0.1):
    if not isinstance(keys, list):
        keys = [keys]
    
    for key in keys:
        with pyautogui.hold(key):
            time.sleep(interval)

###
# Logique FF3 3DR
##################

def ff3_3dr_launcher_is_running():
    return detection_application("FF3_Launcher.ex")

def demarrer_ff3_3dr_launcher():
    subprocess.Popen([STEAM_EXE, f"steam://rungameid/{FF3_3DR_APP_ID}"])

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

def detection_initiale(debug = True):
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
        print("Ni dans le jeu, ni dans le menu, on recommence")

    if debug:
        print("Configuration initiale terminé!!!")

if __name__ == "__main__":
    from datetime import datetime
    start = datetime.now()

    # Détection du ratio (scaling) de l'écran
    RATIO = get_scaling_ratio()

    screenSaver = ScreenSaver()
    try:
        screenSaver.disable()

        # Se rendre jusque dans le jeu
        detection_initiale()

        # Logique automatisée
        #main_loop(script = lvl_up)
        main_loop(script = lvl_jobs, delai_deplacement = 0)
    except KeyboardInterrupt:
        pass
    finally:
        screenSaver.enable()

        end = datetime.now()
        print(end - start)
