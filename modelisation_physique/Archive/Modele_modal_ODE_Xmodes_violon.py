# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:10:51 2023

@author: Romain Caron
"""
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import platform
import time as tim
import soundfile as sf
import os
import sounddevice as sd
import tempfile

#------------------------------------------------Contrôle

gamma = 0.6
zeta = 0.3

Fb=2; #Force normale à la corde appliquée par l'archet
vb=0.1; #Vitesse transversale de l'archet

#------------------------------------------------Paramètres d'entrée

nb_mode=3;          #Nombre de modes à modéliser
dur=2;              #Durée de l'enregistrement à produire en secondes 

#-----------------------------Clarinette
W = 3e-2            #Largeur de la bouche
H = 2e-3            #Longueur de la bouche
gamma_air = 1.4     #Indice adiabatique
rho = 1.292         #Masse vol air
c = 343             #Vitesse son
rc = 3e-2           #rayon de la clarinette
Lc = 60e-2          #longueur clarinette
Sc = np.pi*rc**2    #section clarinette
pM = 0.1            #Pression de plaquage statique


#------------------------------Corde
#Tc=27*9.81/4;          #Tension de la corde (27kg pour 4 cordes)
Tc=27*9.81/12.5; #G3
dc=0.9e-3;           #Diamètre corde
Ec=500e6;            #Module d'Young corde
#rhoc=2700;          #Masse volumique corde
rhoc=5000;
Lc=328e-3;          #Longueur corde violon
v0=1;             #Coefficient v0

Ic=np.pi*dc**4/64;    #Moment quadratique corde


#------------------------------------------Admittances
Y_m=np.ones(nb_mode)*1 /1233.36096998528    #Initialisation de toutes les admittances à une valeur par défaut
Y_m[0] = 1 /1233.36096998528                #Admittance au premier mode
#Y_m[1] = 1 /1233.36096998528                #Admittance au deuxième mode
#Y_m[2] = 1 /1233.36096998528

#------------------------------------------Fréquences

f=np.zeros(nb_mode)                 #Initialisation générale fréquences des modes
Leff=Lc                             #Cas Clarinette Zs=0
Leff=Lc+(8*rc/(3*np.pi))            #Cas Clarinette bafflée
#Leff=Lc+0.6*rc                     #Cas Clarinette non bafflée
#f=np.array([(2*n+1)*c/(4*Leff) for n in range(nb_mode)]) #Cas particulier de la clarinette (quintoie)
f=np.array([(n*np.pi)/(2*Lc)*np.sqrt(Tc/(rhoc*(np.pi*(dc/2)**2)))*np.sqrt(1+((Ec*Ic/(2*Tc))*(n**2*np.pi**2/(Lc**2)))) for n in range(1,nb_mode+1)]) #Cas particulier du violon uniquement corde
"""
f[0] = 220                     #Fréquence premier mode ajustée à la main
f[1] = 440                     #Fréquence deuxième mode
f[2] = 660
f[3] = 880
f[4] = 1100"""
#------------------------------------------------Variables générales

fs = 44100          #Fréquence d'échantillonnage


#------------------------------------------------Variables calculées
omega=np.array([x*2*np.pi for x in f])                  #Conversion freq/puls
F=np.array([2*(x)* c / Lc for x in range(1,nb_mode+1)])   #Coefficients modaux
time = np.linspace(0,3,fs*3)                            #Vecteur temps

#zeta = W*H/Sc*np.sqrt(2*gamma_air*rho/pM)              #Valeur de zeta en fonction des paramètres de la bouche   

A = zeta*(3 * gamma - 1) / 2 /np.sqrt(gamma)            #Paramètres pour l'équation du modèle
B = -zeta*(3*gamma+1)/8/gamma**(3/2)
C = -zeta*(gamma +1)/16/gamma**(5/2)


args = (A, B, C,F,omega,Y_m,v0,vb,Fb)                            #Encapsulation des paramètres pour la résolution

#--------------------------------Vecteurs utiles pour les calculs
deriv_index = np.array([x%2 for x in range(nb_mode*2)])        #Vecteur à multiplier avec X pour avoir les dérivées uniquement
func_index=np.array([(x+1)%2 for x in range(nb_mode*2)])    #Vecteur à multiplier avec X pour avoir les non-dérivées uniquement
x_out=np.zeros(nb_mode*2)                               
Fbis=np.zeros(nb_mode*2)                                #Conversion de F pour qu'il fasse la taille nb_mode*2
Fbis[1::2]=F
omegabis=np.zeros(nb_mode*2)
omegabis[::2]=omega
Y_mbis=np.zeros(nb_mode*2)
Y_mbis[1::2]=Y_m


#---------------------------------------Méthodes de Runge-Kutta 

def RK1(X,args):                    #Ordre 1
    dt=1/fs
    x2=np.zeros(fs*dur)
    x2[0]=sum(func_index*X)
    for i in range(fs*dur-1):
        Xs=[x*dt for x in funtion(X,args)]
        X=np.add(X,Xs)
        x2[i+1]=sum(func_index*X)     
    return x2

def RK2(X,args):                    #Ordre 2
    dt=1/fs
    x2=np.zeros(fs*dur)
    x2[0]=sum(func_index*X)
    for i in range(fs*dur-1):
        Xp=[x*dt/2 for x in funtion(X,args)]
        #print(Xp)
        Xs=[x*dt for x in funtion(np.add(X,Xp),args)]
        X=np.add(X,Xs)
        #print(Xs)
        x2[i+1]=sum(func_index*X)
    return x2

def RK4(X,args):                    #Ordre 4
    dt=1/fs
    x2=np.zeros(fs*dur)
    x2[0]=sum(func_index*X)
    for i in range(fs*dur-1):
        k1=funtion(X,args)
        
        k1x=[x*dt/2 for x in k1]
        k2=funtion(np.add(X,k1x),args)
        
        k2x=[x*dt/2 for x in k2]
        k3=funtion(np.add(X,k2x),args)
        
        k3x=[x*dt for x in k3]
        k4=funtion(np.add(X,k3x),args)
        
        k2s=[x*2 for x in k2]
        k3s=[x*2 for x in k3]
        #print(k1)
        Xs=np.add(np.add(np.add(k1,k2s),k3s),k4)
        Xsx=[x*dt/6 for x in Xs]
        X=np.add(X,Xsx)
        #print(Xs)
        x2[i+1]=sum(func_index*X)
    return x2

#---------------------------------------- Définition du système \Dot{X}=f(X)

def funtion(x,args):
    (A, B, C,F,omega,Y_m,v0,vb,Fb)  = args
    xderiv_index=sum(x*deriv_index)
    xfunc_index=sum(x*func_index)
    #commun=sum(x*deriv_index)*(A+2*B*sum(x*func_index)+3*C*sum(x*func_index)**2) #Spécifique à la clarinette
    commun=Fb*v0*xderiv_index*(2*vb*xfunc_index-xfunc_index**2+v0**2)/(-2*vb*xfunc_index+xfunc_index**2+v0**2)
    x_out=np.zeros(nb_mode*2)
    x_out[1:]=Fbis[1:]*commun-(Y_mbis*x)[1:]-(np.power(omegabis,2)*x)[:-1]
    x_out[:-1]=x_out[:-1]+(x*deriv_index)[1:]

    return x_out


#------------------------------------------ Fonction pour jouer le son et enregistrer le wav
def play(y,Fe=44100):
    rep=1
    z=np.real(y)/(abs(np.real(y)).max())
    if platform.system()=='Darwin': #MAC (sous linux sounddevice a un comportement erratique)
        sd.play(z,Fe)
        return
    fichier=tempfile.mktemp()+'SON_TP.wav'
    sec=len(y)/Fe
    if sec<=20:
        rep=True
    if sec>20:
        print ('Vous allez créer un fichier son de plus de 20 secondes.')
        rep=None
        while rep is None:
            x=input('Voulez-vous continuer? (o/n)')
            if x=='o':
                rep=True
            if x=='n':
                rep=False
            if rep is None:
                print ('Répondre par o ou n, merci. ')
    if rep:
        fichier2='C:/Users/GaHoo/Desktop/Cours/ATIAM/9. PAM/Code/son.wav' #Adresse du fichier exporté, à modifier
        sf.write(fichier,z,Fe)
        sf.write(fichier2,z,Fe)     #Ecrit le fichier wav dans le fichier
        os.system(''+fichier+' &')
        
#------------------------------------------------Moteur

t1=tim.time()                   #Démarrage du timer

X=[gamma*i for i in func_index]     #Initialisation de X avec p_n=gamma à l'instant 0

p=RK4(X,args)                   #Appel de la résolution
tcalc=tim.time()-t1             #Arrêt du timer
print("Temps de calcul : "+str(tcalc)+"s")
play(p)                         #Ecoute du son


#-----------------------------------------------Plots
plt.plot(time, p, 'orange', linewidth = 2)
plt.xlabel('time (s)')
plt.ylabel('pressure')
plt.xlim(0,0.5)
plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
#plt.ylim(0,0.000000000001)
plt.xlim()
plt.grid(True)

