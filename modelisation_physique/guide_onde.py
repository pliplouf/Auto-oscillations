"""
@author : Clémentine BERGER & Amélie PICARD

Implémentation guide d'onde suivant l'article de McIntyre : à l'avantage d'être plus modulable
avec la possibilité de changer de fonction de réflexion au bout du guide d'onde

Ce script fonctionne pour une simulation de longueur L et pour une corde pincée en son MILIEU
"""


### Importation des bibliothèques

import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as sig
import scipy.integrate as intgr

### Paramètres utilisateurs

# c = célérité des ondes sonores
# L = longueur du guide d'onde
# gamma = rapport pression de bouche / pression de plaquage
# zeta = paramètre caractéristique de l'anche
# type_reflection = dirac ou triangle (essayer de rajouter gaussien)
# frac_T = pour le type triangle -> défini la demi largeur du triangle égale à T/frac_T


### Définition des fonctions


def retardT(l, c0):
    """
    Renvoie T le retard accumulé par l'onde
    en un aller-retour
    l : longueur du guide cylindrique
    c0 : célérité des ondes dans l'air
    """
    return 2 * l / c0


def coeffs(gamma, zeta):
    """Calcule les coefficients de la fonction de
    couplage F linéarisée
    F(p) = F0 + Ap + Bp**2 + Cp**3
    """
    if gamma == 0:
        return 0, 0, 0, 0
    else:
        F0 = zeta * (1 - gamma) * np.sqrt(gamma)
        A = zeta * (3 * gamma - 1) / 2 / np.sqrt(gamma)
        B = -zeta * (3 * gamma + 1) / 8 / gamma ** (3 / 2)
        C = -zeta * (gamma + 1) / 16 / gamma ** (5 / 2)
    return F0, A, B, C


def Fclarinette(list_p, gamma, zeta):
    """
    Renvoit le débit u suivant la pression p
    suivant la relation u = F(p)
    """
    if gamma == 0:
        return np.zeros(len(list_p))
    else:
        valid = (gamma - list_p < 1) & (gamma - list_p > 0)
        sgn = (gamma-list_p)/np.abs(gamma-list_p)
        #u = zeta * (1 - gamma + list_p) * np.nan_to_num(np.sqrt(gamma - list_p)) * valid
        u = zeta * (1 - gamma + list_p) * np.sqrt(np.abs(gamma - list_p)) * valid * sgn
    return u


def tableau_Fsimulation(pmin, pmax, nb_pts, gamma, zeta):
    """
    Rempli un tableau F pour faire la recherche de 0

    pmin = borne inférieure de p
    pmax = borne supérieure de p
    nb_pts = nombre de points de calculs
    gamma =
    zeta =
    """
    tab_p = np.linspace(pmin, pmax, nb_pts)
    tab_F = Fclarinette(tab_p, gamma, zeta)

    return tab_p, tab_F


def find_zero(tableau, i):
    """
    Recherche le point d'annulation de tableau le plus proche possible de i

    tableau = tableau des valeurs de la fonction F sur l'intervalle souhaité
    i =
    """
    taille = len(tableau)
    changement_signe = (
        tableau[0 : taille - 1] * tableau[1:taille]
    )  # il y a un point d'annulation entre tableau[j] et tableau[j+1] ssi tableau[j]*tableau[j+1] <= 0
    negatif = changement_signe <= 0  # True aux indices où il y a un changement de signe
    tab_i0 = (np.arange(taille - 1))[
        negatif
    ]  # indices auxquels il y a un changement de signe
    if len(tab_i0) == 0:
        return np.argmin(np.abs(tableau))
    i0 = np.argmin(
        np.abs(tab_i0 - i)
    )  # indice de l'indice le plus proche de i dans tab_i0
    return tab_i0[i0]


def convolution(ind_tau, reflex_list, signal_list):
    """
    Calcul de la convolution entre le signal p + u et la fonction de réflexion
    (aux temps passés) avec une intégration par la méthode des trapèzes

    ind_tau = indice du temps de calcul courant
    reflex_list = liste des coefficients de réflexion dans le temps
    signal_list = liste p + u

    (plus rapide que scipy...)
    """

    x1 = reflex_list[0 : ind_tau + 1]
    x2 = np.flipud(signal_list[0 : ind_tau + 1])

    integrate = intgr.trapz(y=x1 * x2)
    # integrate = intgr.trapz(reflex_list*np.flipud(signal_list))

    return integrate


def convolution_triangle(ind_tau, T, fe, frac_T, reflex_list, signal_list):
    """
    Calcul de la convolution entre le signal p + u et la fonction de réflexion
    (aux temps passés) avec une intégration par la méthode des trapèzes

    ind_tau = indice du temps de calcul courant
    reflex_list = liste des coefficients de réflexion dans le temps
    signal_list = liste p + u

    (plus rapide que scipy...)
    """

    indT = int(T * fe)

    delta_ind = indT // frac_T

    if ind_tau <= indT - delta_ind:
        return 0

    elif ind_tau <= indT + delta_ind:
        x1 = reflex_list[indT - delta_ind : ind_tau + 1]
        x2 = np.flipud(signal_list[0 : ind_tau - (indT - delta_ind) + 1])

    else:
        x1 = reflex_list[indT - delta_ind : indT + delta_ind + 1]
        x2 = np.flipud(
            signal_list[ind_tau - (indT + delta_ind) : ind_tau - (indT - delta_ind) + 1]
        )

    integrate = intgr.trapz(y=x1 * x2)

    return integrate


def reflexion(T, pertes_dirac,frac_T, rate_gauss, fe, Nsim, type):
    """
    Calcule la liste des coefficients de réflexion pour plusieurs formes de fonction de réflexion

    type = str donnant le type de réflexion choisi ; 'dirac', 'triangle'
    (si possible 'exponentiel' mais nécessite de revoir un peu le code...)
        - dirac : r(t) = -delta(t-T)
        - triangle : triangle négatif centré en T (plus il est court, plus on se rapproche du dirac et des créneaux)
        - gaussienne : -a*exp(-b(t-T)**2)
    """
    
    indT = int(T*fe)   #indice du moment T de la réflexion au bout du guide
    
    
    if type == 'dirac' :
        reflex_list = np.zeros(Nsim)
        reflex_list[indT] = -pertes_dirac

    elif type == "triangle":  # centré en T
        reflex_list = np.zeros(Nsim)
        delta_ind = indT // frac_T
        pente = 1 / delta_ind

        for i in range(indT - delta_ind, indT + 1):
            reflex_list[i] = (i - indT + delta_ind) * pente

        for i in range(indT + 1, indT + delta_ind + 1):
            reflex_list[i] = reflex_list[indT] - (i - indT) * pente

        aire = np.sum(reflex_list)
        #aire = intgr.trapz(y=reflex_list,dx=1/fe)
        #aire = np.max(abs(reflex_list))
        
        reflex_list = -reflex_list/aire 
        
    elif type == 'gauss':
        demi_largeur = rate_gauss*T
        sigma = demi_largeur/np.sqrt(2*np.log(2))
        b = 1/(2*(sigma**2))
        a = 1/(sigma*np.sqrt(2*np.pi))    ### à revoir, le fait que l'aire de r doit être égale à 1
        tps = np.linspace(0,Nsim/fe,Nsim)
        reflex_list = -np.exp(-b*((tps-T)**2))
        #aire = intgr.trapz(y=reflex_list,dx=1/fe)
        #aire = np.max(abs(reflex_list))
        aire = np.sum(abs(reflex_list))
        reflex_list /= abs(aire)
                    
    return reflex_list


def simulation(t_max,sample_rate,gamma,zeta,type_reflection,l,c0,pertes_dirac=1,frac_T=10,rate_gauss=0.1,fig=False,sound=False):
    """
    Renvoit la pression p et le débit u (adimensionnés) simulés avec
    les paramètres gamma, zeta :

    t_max : durée de la simulation en s
    fe : fréquence d'échantillonnage de la simulation en Hz
    gamma : contrôle de la pression de bouche
    zeta : contrôle anche
    type_reflection : type de réflexion au bout du guide, 'dirac', 'triangle' ou 'gauss'
    frac_T : seulement pour le type 'triangle', définition de la demi-largeur du triangle T/frac_T
    rate_gauss : demi-largeur à mi-hauteur (typiquement entre 0.05 et 0.4)
    l : longueur du cylindre
    c0 : célérité des ondes
    """

    # Initialisation des paramètres
    T = retardT(l, c0)
    indT = int(T * sample_rate)

    # F0, A, B, C = coeffs(gamma, zeta)

    time = np.arange(int(t_max * sample_rate)) / sample_rate  # temps de simulation
    Nsim = len(time)

    p = np.zeros(Nsim)
    u = np.zeros(Nsim)

    reflex_list = reflexion(
        T, pertes_dirac,frac_T, rate_gauss, sample_rate, Nsim, type=type_reflection
    )

    ######## SIMULATION

    tab_p, tab_F = tableau_Fsimulation(-5, 5, 2000, gamma, zeta)
    solvF = tab_p - tab_F

    i_act = np.argmin(np.abs(tab_p - gamma)) + 1

    if type_reflection == "dirac":
        for j in range(Nsim):
            if j < indT:
                ph = 0
            else:
                ph = -(p[j - indT] + u[j - indT])
            i = find_zero(solvF - ph, i_act)
            i_act = i
            p[j] = tab_p[i]
            u[j] = tab_F[i]
            # u[j] = Fclarinette(np.array(p[j]),gamma,zeta)
            # disc = (A-1)**2 -4*B*(F0+ph)
            # p_fixe = (1-A-np.sqrt(disc))/(2*B)
            # p_fixe = (ph+F0)/(1-A)
            # p[j] = p_fixe
            # u[j] = F(np.array([p_fixe]),gamma,zeta)

    elif type_reflection == "triangle":
        for j in range(Nsim):
            ph = convolution_triangle(ind_tau=j,T=T,fe=sample_rate,frac_T=frac_T,reflex_list=reflex_list,signal_list=p + u)
            #ph = convolution(ind_tau=j,reflex_list = reflex_list, signal_list = p + u)
            i = find_zero(solvF - ph, i_act)
            i_act = i
            p[j] = tab_p[i]
            u[j] = tab_F[i]
            #p_fixe = (ph+F0)/(1-A)
            #p[j] = p_fixe
            #u[j] = F(np.array([p_fixe]),gamma,zeta)
            
    elif type_reflection=="gauss":
        for j in range(Nsim): 
            ph = convolution(ind_tau=j,reflex_list = reflex_list, signal_list = p + u)
            #print(ph)
            i = find_zero(solvF-ph,i_act)
            i_act = i
            p[j] = tab_p[i]
            u[j] = tab_F[i]
            # p_fixe = (ph+F0)/(1-A)
            # p[j] = p_fixe
            # u[j] = F(np.array([p_fixe]),gamma,zeta)

    if fig:
        plt.figure(figsize=(10, 5))
        plt.plot(time, p)
        plt.xlim(0, 0.2)
        plt.ylim(-1.1, 1.1)
        plt.tight_layout()
        plt.xlabel("Temps en s", size=14)
        plt.ylabel("Amplitude", size=14)
        plt.show()

    # if sound :
    #    display(Audio(p,rate=fe))

    return p, u



####### Instruments à cordes frottées (marche paaaaaas pour l'instant, oubli Léo)

def Fcordes(delta_v, v0, Fb,fig=False):
    result = Fb*(delta_v/v0)/(1+(delta_v/v0)**2)
    if fig:
        plt.plot(delta_v, result)
    return result

def tableau_Fcordes(vmin, vmax, nb_pts, v0, Fb):
    """
    Rempli un tableau F pour faire la recherche de 0

    vmin = borne inférieure de dv
    vmax = borne supérieure de dv
    nb_pts = nombre de points de calculs
    """
    tab_v = np.linspace(vmin, vmax, nb_pts)
    tab_f = Fcordes(tab_v, v0, Fb)

    return tab_v, tab_f

def cordes(t_max,sample_rate,v0,Fb,type_reflection,L,c0,pertes_dirac=1,frac_T=10,rate_gauss=0.4,fig=False,sound=False):
    """
    Renvoit la différence de vitesse dv et la force transverse f (adimensionnés) simulés avec
    les paramètres gamma, zeta :

    t_max : durée de la simulation en s
    fe : fréquence d'échantillonnage de la simulation en Hz
    gamma : contrôle de la pression de bouche
    zeta : contrôle anche
    type_reflection : type de réflexion au bout du guide, 'dirac', 'triangle' ou 'gauss'
    frac_T : seulement pour le type 'triangle', définition de la demi-largeur du triangle T/frac_T
    rate_gauss : demi-largeur à mi-hauteur (typiquement entre 0.05 et 0.4)
    L : longueur du cylindre
    c : célérité des ondes
    """

    # Initialisation des paramètres
    T = retardT(L, c0)
    indT = int(T * sample_rate)

    # F0, A, B, C = coeffs(gamma, zeta)

    time = np.arange(int(t_max * sample_rate)) / sample_rate  # temps de simulation
    Nsim = len(time)

    dv = np.zeros(Nsim)
    f = np.zeros(Nsim)

    reflex_list = reflexion(
        T, pertes_dirac,frac_T, rate_gauss, sample_rate, Nsim, type=type_reflection
    )

    ######## SIMULATION

    tab_v, tab_f = tableau_Fcordes(0, 100, 2000, v0, Fb)
    solvF = tab_v - tab_f

    i_act = np.argmin(solvF) + len(solvF)//3

    if type_reflection == "dirac":
        for j in range(Nsim):
            if j < indT:
                vh = 0
            else:
                vh = -(dv[j - indT] + f[j - indT])
            #plt.plot(solvF - vh)
            #break
            i = find_zero(solvF - vh, i_act)
            i_act = i
            #print(i_act)
            dv[j] = tab_v[i]
            f[j] = tab_f[i]
            # disc = (A-1)**2 -4*B*(F0+ph)
            # p_fixe = (1-A-np.sqrt(disc))/(2*B)
            # p_fixe = (ph+F0)/(1-A)
            # p[j] = p_fixe
            # u[j] = F(np.array([p_fixe]),gamma,zeta)

    elif type_reflection == "triangle":
        for j in range(Nsim):
            ph = convolution_triangle(
                ind_tau=j,
                T=T,
                fe=sample_rate,
                frac_T=frac_T,
                reflex_list=reflex_list,
                signal_list=dv + f,
            )
            i = find_zero(solvF - vh, i_act)
            i_act = i
            dv[j] = tab_v[i]
            f[j] = tab_f[i]
            #p_fixe = (ph+F0)/(1-A)
            #p[j] = p_fixe
            #u[j] = F(np.array([p_fixe]),gamma,zeta)
            
    elif type_reflection=="gauss":
        for j in range(Nsim): 
            ph = convolution(ind_tau=j,reflex_list = reflex_list, signal_list = dv + f)
            #print(ph)
            i = find_zero(solvF-vh,i_act)
            i_act = i
            dv[j] = tab_v[i]
            f[j] = tab_f[i]
            # p_fixe = (ph+F0)/(1-A)
            # p[j] = p_fixe
            # u[j] = F(np.array([p_fixe]),gamma,zeta)

    if fig:
        plt.figure(figsize=(10, 5))
        plt.plot(time, dv)
        plt.xlim(0, 0.2)
        plt.ylim(-1.1, 1.1)
        plt.tight_layout()
        plt.xlabel("Temps en s", size=14)
        plt.ylabel("Amplitude", size=14)
        plt.show()

    # if sound :
    #    display(Audio(p,rate=fe))

    return dv, f