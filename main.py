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
import logging

SUPPORTED_SESSIONS = ["KDE"]
STEAM_EXE = shutil.which("steam")
FF3_3DR_APP_ID = "239120"

ratio = None
logger = logging.getLogger(__name__)

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
            self.__cookie_ = self.__saver_interface_.Inhibit("ff33dr_automater", "Farming")

    def enable(self):
        if self.__cookie_ is not None:
            self.__saver_interface_.UnInhibit(self.__cookie_)
            self.__cookie_ = None

class Direction(Enum):
    gauche_droite = 0
    haut_bas = 1

def get_scaling_ratio():
    session = None
    if sys.platform == "linux":
        session = os.environ["XDG_SESSION_DESKTOP"]

    ratio = None
    match session:
        case "KDE":
            from PyQt5.QtGui import QGuiApplication
            app = QGuiApplication(sys.argv)
            screen = app.primaryScreen()
            ratio = screen.devicePixelRatio()
        case _:
            raise NotImplementedError(f"La session '{session}' n'est pas supportée")

    return ratio

def get_scaled_filename(nom_image):
    if ratio is not None:
        nom_image, ext = os.path.splitext(nom_image)
        nom_image = f"{nom_image}-{ratio}{ext}"

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

def attendre_image(nom_image, boucler = True, temps_attente = 1.0, keys = None, **kwargs):
    nom_image = get_scaled_filename(nom_image)
    while True:
        try:
            logger.info(f"Détection de l'image {nom_image}")
            sc = screenshotFix()
            res = pyautogui.locate(nom_image, sc, **kwargs)
            return res
        except ImageNotFoundException:
            logger.info(f"L'image {nom_image} n'a pas été trouvé")
            if keys is not None:
                pressFix(keys)
            if boucler:
                logger.info("On attend et on réesaye la détection")
                time.sleep(temps_attente)
            else:
                return None

###
# Correctifs de problèmes de la librairie pyautogui
####################################################

from tempfile import NamedTemporaryFile
from PIL import Image
import pyscreenshot as ImageGrab
def screenshotFix(imageFilename = None, region = None, prefix = "ff3-3dr-", delete = True):
    if imageFilename is None:
        tmpFile = NamedTemporaryFile(prefix = prefix, suffix = ".png", delete_on_close = False, delete = delete)
        tmpFile.close()
        tmpFilename = tmpFile.name
    else:
        tmpFilename = imageFilename
    logger.debug(f"Fichier temporaire: {tmpFilename}")

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
        logger.info("Cliquer sur le bouton 'JOUER' pour démarrer le jeu Final Fantasy III (3D Remake)")
        pyautogui.click(pyautogui.center(res))

def detection_menu_principal(attendre = True):
    res = attendre_image("screenshots/ff3/menu.png", keys = ["enter"], boucler = False)
    return res is not None

def demarrer_partie():
    logger.info("Démarrage de la partie (enter + enter)")
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
            logger.info("Activation du combat automatique")
            pressFix("a")
        else:
            logger.info("Le combat automatique n'est pas activé")
            return False
    else:
        logger.info("Le combat automatique est déjà activé")

    return True

class Action(Enum):
    bloquer = 0
    voler = 1

def executer_actions(action, interval = 0.2):
    for j in range(4):
        logger.info(f"Attente du début de l'action du personnage {j}")
        attendre_prochain_tour()
        logger.info(f"Le tour du personnage {j} est démarré")
        match action:
            case "voler":
                logger.info(f"Voler avec le personnage {j}")
                voler(interval)
            case _:
                logger.info(f"Bloquer avec le personnage {j}")
                bloquer(interval)

def bloquer(interval = 0.2):
    pressFix(["down", "down", "enter"], interval = interval)

def voler(interval = 0.2):
    pressFix(["down", "enter"], interval = interval)

def attaquer(interval = 0.2):
    pressFix(["enter", "enter"], interval = interval)

def attendre_prochain_tour(attendre = True):
    while attendre_image("screenshots/ff3/debut-tour.png", boucler = False, confidence = 0.9) is None:
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

# Pour monter de niveau une job, il faut effectuer des "actions". Le script
# prend pour acquis que le grinding s'effectue dans un endroit où les ennemis
# sont de bas niveau (ex: début du jeu). Pour monter de niveau, il faut effectuer
# un nombre total d'actions qui dépend de la job attitrée à un personnage (6-8).
#
# Le script va activer l'action de bloquer pour chaque personnage pendant 6 tours
# par combat, ce qui devrait normalement augmenter le niveau de job de chaque personnage
# de 1 par combat. Il n'est pas possible de monter deux fois de niveau pour un même
# combat.
def lvl_jobs(combat_rapide = True, nombre_garde = 6, action = Action.bloquer):
    # Désactiver l'attaque automatique, si elle était déjà activée
    # @todo: La détection s'effectue probablement avant que le combat soit vraiment démarré
    if valider_attaque_automatique(activer = False):
        logger.info("Désactivation de l'attaque automatique")
        pressFix("a")

    # Pour le combat rapide, on commence par bloquer et ensuite, on active
    # le mode automatique pendant une certaine période de temps
    if combat_rapide:
        logger.info("Action initiale")
        executer_actions(action)
        logger.info(f"Démarrage de l'attaque automatique pour {nombre_garde} tours")
        # Activer l'attaque automatique
        valider_attaque_automatique(activer = True)
        # Ça prend environs 5 secondes par tour
        time.sleep(5 * nombre_garde)
        logger.info("Désactivation de l'attaque automatique")
        pressFix("a")
    # Pour le mode lent, on bloque un certain nombre de tours, sans activer le combat automatique.
    # Ce mode est 3-4 fois plus lent que le combat rapide pour le même nombre d'actions.
    else:
        # Bloquer 6 fois pour monter de niveau
        for i in range(nombre_garde):
            logger.info(f"Tour de combat #{i}")
            executer_actions(action)

    attendre_prochain_tour()
    for i in range(4):
        logger.info(f"Attaque avec le personnage {i}")
        attaquer()
        time.sleep(0.4)
    
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
                logger.info("Se déplacer pour démarrer un combat")
                with pyautogui.hold(direction1):
                    if est_en_combat(attendre = False):
                        break
                    time.sleep(delai_deplacement)
                with pyautogui.hold(direction2):
                    if est_en_combat(attendre = False):
                        break
                    time.sleep(delai_deplacement)
            
            logger.info("---------------------- Combat démarré ----------------------")
            script()
            logger.info("---------------------- Combat terminé ----------------------")
            detection_in_game(keys = ["enter", "enter", "enter"], temps_attente = 0.2)
        except pyautogui.FailSafeException:
            pass

def detection_initiale():
    if not ff3_3dr_is_running():
        if not ff3_3dr_launcher_is_running():
            if not steam_is_running():
                logger.info("Steam n'est pas en cours d'exécution, on le démarre")
                demarrer_steam()
            else:
                logger.info("Steam est déjà démarré")

            logger.info("Démarrage de FF3 3D Remake")
            demarrer_ff3_3dr_launcher()

        detection_launcher(demarrer_jeu = True)
    else:
        logger.info("Le jeu FF3 3D Remake est déjà démarré")

    while not detection_in_game(attendre = False):
        if detection_menu_principal(attendre = False):
            demarrer_partie()
        logger.info("Ni dans le jeu, ni dans le menu, on recommence")

    logger.info("Configuration initiale terminé!!!")

if __name__ == "__main__":
    from datetime import datetime
    start = datetime.now()

    logging.basicConfig(format = "%(asctime)s - %(message)s", level = logging.INFO)

    # Détection du ratio (scaling) de l'écran
    ratio = get_scaling_ratio()
    logger.info(f"Le ratio de l'écran est: {ratio}")

    screenSaver = ScreenSaver()
    try:
        logger.info("Désactivation du screensaver")
        screenSaver.disable()

        # Se rendre jusque dans le jeu
        logger.info("====================== DETECTION INITIALE ======================")
        detection_initiale()

        # Logique automatisée
        logger.info("====================== MAIN LOOP ======================")
        # Script général pour monter de niveau
        #main_loop(script = lvl_up)

        # Script optimisé pour monter le niveau des jobs
        main_loop(script = lvl_jobs, delai_deplacement = 0)

        # Script optimisé pour monter le niveau des jobs (version voleur, qui ne peut pas bloquer)
        #main_loop(script = lvl_job, delai_deplacement = 0, action = Action.voler)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Réactivation du screensaver")
        screenSaver.enable()

        end = datetime.now()
        logger.info(end - start)
