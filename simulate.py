import Shadow
import numpy
from pyplanemono.elements import PGM, Plane_Mirror, Grating # Classes for PGM, Plane Mirror and Grating
from pyplanemono.shadow.tools import config_oe, get_eff, initial_read
from tqdm.gui import tqdm
import csv
import matplotlib.pyplot as plt
from multiprocessing import Pool, set_start_method
from datetime import datetime
import scipy.interpolate as ip



set_start_method("spawn", force=True) # Required for multiprocessing on Windows
iwrite = 0

def trace(list_oe: list, beam: Shadow.Beam)-> tuple:
    """
    Custom trace function to trace the beam through the optical elements,
    calculate the FWHM of the beam at the exit slit and return the intensity
    at the exit slit.

    Parameters:
    list_oe: list
        List of optical elements to trace the beam through
    beam: Shadow.Beam
        Beam object to trace through the optical elements
    
    Returns:
    fwhm: float
        Full width at half maximum of the beam at the exit slit
    intensity_val: float
        Intensity of the beam at the exit slit
    int_dict: dict
        Dictionary of the intensity at each optical element
    height_dict: dict
        Dictionary of the FWHM of the beam at each optical element
    ray_dict: dict
        Dictionary of the number of rays at each optical element
    
    """
    iwrite = 0
    num_oe = len(list_oe)
    int_dict = {}
    height_dict = {}
    ray_dict = {}
    for i in range(num_oe):
        oe = list_oe[i]
        print(f"Running optical element: {i+1}")
        if iwrite:
            oe.write(f"start.{i:02d}")
        
        
        
        # Redirect stdout and stderr to the file
        beam.traceOE(oe, i+1)
        num_of_rays= len(beam.getshonecol(23, nolost=1))
        intensity_val = beam.getshonecol(23, nolost=1).sum()
        int_dict[f"OE{i+1}"] = intensity_val
        if num_of_rays < 500:
            height_dict[f'OE{i+1}'] = 0
            ray_dict[f"OE{i+1}"] = 0
        else:
            height_dict[f'OE{i+1}'] = beam.histo1(3, nbins=50, nolost=1)['fwhm']
            ray_dict[f"OE{i+1}"] = num_of_rays
        print(f"Intensity after OE{i+1}: {intensity_val}")

        if i == 10:
            
            if num_of_rays < 500:
                print("Number of rays too low, skipping")
                return 0, 0, int_dict, height_dict, 0
            else:
                result = Shadow.ShadowTools.histo1(beam, 11, nbins=50, nolost=1)
                if result['fwhm'] == 0 or result['fwhm'] == None: # Occasionally SHADOW struggles to fit FWHM, skip if this happens
                    print("FWHM too low, skipping")
                    return 0, 0, int_dict, height_dict, 0
                
                return result['fwhm'], intensity_val, int_dict, height_dict, ray_dict


def set_up(E, delta_E, cff, order):
    """
    Function to set up the optical elements and beam for the simulation

    Parameters:
    E: float
        Energy of the beam in eV
    delta_E: float
        Energy range to simulate in eV
    cff: float
        Fixed focus constant of the PGM
    order: int
        Grating order to simulate
    
    Returns:
    list_oe: list
        List of optical elements to trace the beam through
    beam: Shadow.Beam
        Beam object to trace through the optical elements
    """ 
        
    iwrite = 0

    #
    # initialize shadow3 source (oe0) and beam
    #

    pgm = PGM(mirror = Plane_Mirror(), grating = Grating())

    pgm.energy = float(E)
    pgm.grating.line_density = 400.
    pgm.cff = cff
    pgm.beam_offset = -13.
    pgm.mirror.hoffset =40.
    pgm.mirror.voffset = 13.
    pgm.mirror.axis_voffset = 6.5
    pgm.grating.order = int(order)
    pgm.grating.dimensions = [200, 23, 50]

    pgm.grating.compute_angles()
    pgm.set_theta()
    pgm.generate_rays()
    _ = pgm.grating.compute_corners()
    _ = pgm.mirror.compute_corners()



    beam = Shadow.Beam()
    oe0 = Shadow.Source() # Bending Magnet Source
    oe1 = Shadow.OE() # Toroidal M1
    oe2 = Shadow.OE() # Fictitious slit 1
    oe3 = Shadow.OE() # Plane M2
    oe4 = Shadow.OE() # Grating
    oe5 = Shadow.OE() # Fictitious slit 2
    oe6 = Shadow.OE() # Spherical M3
    oe7 = Shadow.OE() # Exit slit 
    oe8 = Shadow.OE() # Spherical M4
    oe9 = Shadow.OE() # Ellipsoidal M5

    oe_s2 = Shadow.OE() # Slit 2
    oe_s3 = Shadow.OE() # Slit 3

    # Bending Magnet Source
    oe0.BENER = 3.0
    oe0.EPSI_X = 2.7e-06
    oe0.EPSI_Z = 8.2e-09
    oe0.FDISTR = 4
    oe0.FSOURCE_DEPTH = 4
    oe0.F_COLOR = 3
    oe0.F_PHOT = 0
    oe0.HDIV1 = 0.001
    oe0.HDIV2 = 0.001
    oe0.ISTAR1 = 1
    oe0.NCOL = 0
    oe0.N_COLOR = 0
    oe0.NPOINT = 50000
    oe0.PH1 = E - delta_E
    oe0.PH2 = E + delta_E
    oe0.POL_DEG = 0.0
    oe0.R_ALADDIN = 7147.8020399604
    oe0.R_MAGNET = 7.147802039960401
    oe0.SIGDIX = 0.0
    oe0.SIGDIZ = 0.0
    oe0.SIGMAX = 0.0545
    oe0.SIGMAY = 0.0
    oe0.SIGMAZ = 0.0154
    oe0.VDIV1 = 0.00025
    oe0.VDIV2 = 0.00025
    oe0.WXSOU = 0.0
    oe0.WYSOU = 0.0
    oe0.WZSOU = 0.0

    # M1c Toroidal Mirror
    oe1.ALPHA = 90.0
    oe1.DUMMY = 0.1
    oe1.FHIT_C = 1
    oe1.FILE_RIP = b'./misc/B07_m1c_se.dat'
    oe1.FILE_REFL = b'./misc/Rh_15Apr.dat'
    oe1.FMIRR = 3
    oe1.FWRITE = 1
    oe1.F_EXT = 1
    oe1.F_G_S = 2
    oe1.F_RIPPLE = 1
    oe1.F_REFLEC = 1
    oe1.RLEN1 = 700.0
    oe1.RLEN2 = 700.0
    oe1.RWIDX1 = 35.0
    oe1.RWIDX2 = 35.0
    oe1.R_MAJ = 755343.76
    oe1.R_MIN = 504.0
    oe1.T_IMAGE = 10200.0
    oe1.T_INCIDENCE = 88.9
    oe1.T_REFLECTION = 88.9
    oe1.T_SOURCE = 13124.0

    # Fictitious Slit 1
    oe2.ALPHA = 270
    oe2.DUMMY = 0.1
    oe2.FWRITE = 3
    oe2.F_REFRAC = 2
    oe2.F_SCREEN = 1
    oe2.I_SLIT = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    oe2.N_SCREEN = 1
    oe2.RX_SLIT = numpy.array([1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe2.RZ_SLIT = numpy.array([1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe2.T_IMAGE = 0.0
    oe2.T_INCIDENCE = 0.0
    oe2.T_REFLECTION = 180.0
    oe2.T_SOURCE = 0.0

    # Plane mirror M2 (PGM Mirror)
    oe3.ALPHA = 0
    oe3.DUMMY = 0.1
    oe3.FHIT_C = 1
    oe3.FILE_RIP = b'./misc/b07_m2c_se.dat'
    oe3.FILE_REFL = b'./misc/Pt_15Apr.dat'
    oe3.FWRITE = 1
    oe3.F_G_S = 2
    oe3.F_RIPPLE = 1
    oe3.F_REFLEC = 1
    oe3.RLEN1 = 225.0
    oe3.RLEN2 = 225.0
    oe3.RWIDX1 = 30.0
    oe3.RWIDX2 = 30.0
    oe3.T_IMAGE = 0.0
    oe3.T_INCIDENCE = 88.76459254861233
    oe3.T_REFLECTION = 88.76459254861233
    oe3.T_SOURCE = 0.0

    # Grating
    oe4.ALPHA = 180.0
    oe4.DUMMY = 0.1
    oe4.FHIT_C = 1
    oe4.FILE_RIP = b'./misc/B07_PG1c_se.dat'
    oe4.FWRITE = 1
    oe4.F_GRATING = 1
    oe4.F_G_S = 2
    oe4.F_RIPPLE = 1
    oe4.RLEN1 = 100.0
    oe4.RLEN2 = 100.0
    oe4.RULING = 600.0
    oe4.RWIDX1 = 11.5
    oe4.RWIDX2 = 11.5
    oe4.T_IMAGE = 0.0
    oe4.T_INCIDENCE = 89.17645176827041
    oe4.T_REFLECTION = 88.35273332895424
    oe4.T_SOURCE = 0.0

    # Fictitious Slit 2
    oe5.ALPHA = 0
    oe5.DUMMY = 0.1
    oe5.FWRITE = 3
    oe5.F_REFRAC = 2
    oe5.F_SCREEN = 1
    oe5.I_SLIT = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    oe5.N_SCREEN = 1
    oe5.RX_SLIT = numpy.array([1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe5.RZ_SLIT = numpy.array([1000.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe5.T_IMAGE = 0.0
    oe5.T_INCIDENCE = 0.0
    oe5.T_REFLECTION = 180.0
    oe5.T_SOURCE = 0.0

    # Config_oe function will overwrite the values of the four key OEs. (fictitious slit 1, PGM mirror, grating, fictitious slit 2)
    config_oe(pgm, oe4, oe3, oe2, oe5)
    # Consult the config_oe function for more details on what parameters are being overwritten

    # Spherical M3
    oe6.ALPHA = 90.0
    oe6.CIL_ANG = 90.0
    oe6.DUMMY = 0.1
    oe6.FCYL = 1
    oe6.FHIT_C = 1
    oe6.FILE_REFL = b'./misc/Rh_15Apr.dat'
    oe6.FILE_RIP = b'./misc/B07_M3c_se.dat'
    oe6.FMIRR = 1
    oe6.FWRITE = 1
    oe6.F_EXT = 1
    oe6.F_G_S = 2
    oe6.F_RIPPLE = 1
    oe6.F_REFLEC = 1
    oe6.RLEN1 = 300.0
    oe6.RLEN2 = 300.0
    oe6.RMIRR = 209.42887724740214
    oe6.RWIDX1 = 16.0
    oe6.RWIDX2 = 16.0
    oe6.T_IMAGE = 6000.0
    oe6.T_INCIDENCE = 89.0
    oe6.T_REFLECTION = 89.0
    oe6.T_SOURCE = 0.0

    # Exit Slits
    oe7.DUMMY = 0.1
    oe7.FWRITE = 3
    oe7.F_REFRAC = 2
    oe7.F_SCREEN = 1
    oe7.I_SLIT = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    oe7.N_SCREEN = 1
    oe7.RX_SLIT = numpy.array([0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe7.RZ_SLIT = numpy.array([0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe7.T_IMAGE = 4000.0
    oe7.T_INCIDENCE = 0.0
    oe7.T_REFLECTION = 180.0
    oe7.T_SOURCE = 0.0

    # Spherical M4
    oe8.ALPHA = 270.0
    oe8.DUMMY = 0.1
    oe8.FCYL = 1
    oe8.FHIT_C = 1
    oe8.FILE_RIP = b'./misc/B07_M4c_se.dat'
    oe8.FILE_REFL = b'./misc/Rh_15Apr.dat'
    oe8.FMIRR = 1
    oe8.FWRITE = 1
    oe8.F_DEFAULT = 0
    oe8.F_G_S = 2
    oe8.F_RIPPLE = 1
    oe8.F_REFLEC = 1
    oe8.RLEN1 = 300.0
    oe8.RLEN2 = 300.0
    oe8.RWIDX1 = 20.0
    oe8.RWIDX2 = 20.0
    oe8.SIMAG = 4000.0
    oe8.SSOUR = 4000.0
    oe8.THETA = 89.0
    oe8.T_IMAGE = 2500.0
    oe8.T_INCIDENCE = 89.0
    oe8.T_REFLECTION = 89.0
    oe8.T_SOURCE = 0.0

    # Ellipsoidal M5
    oe9.ALPHA = 270.0
    oe9.DUMMY = 0.1
    oe9.FCYL = 1
    oe9.FHIT_C = 1
    oe9.FILE_RIP = b'./misc/B07_M5c_se.dat'
    oe9.FILE_REFL = b'./misc/Rh_15Apr.dat'
    oe9.FMIRR = 2
    oe9.FWRITE = 1
    oe9.F_DEFAULT = 0
    oe9.F_G_S = 2
    oe9.F_RIPPLE = 1
    oe9.F_REFLEC = 1
    oe9.RLEN1 = 300.0
    oe9.RLEN2 = 300.0
    oe9.RWIDX1 = 20.0
    oe9.RWIDX2 = 20.0
    oe9.SIMAG = 1500.0
    oe9.SSOUR = 6500.0
    oe9.THETA = 88.9
    oe9.T_IMAGE = 1500.0
    oe9.T_INCIDENCE = 88.9
    oe9.T_REFLECTION = 88.9
    oe9.T_SOURCE = 0.0

    # Slit 2
    oe_s2.DUMMY = 0.1
    oe_s2.FWRITE = 3
    oe_s2.F_REFRAC = 2
    oe_s2.F_SCREEN = 1
    oe_s2.I_SLIT = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    oe_s2.N_SCREEN = 1
    oe_s2.RX_SLIT = numpy.array([2.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe_s2.RZ_SLIT = numpy.array([11.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe_s2.T_IMAGE = -7097.5
    oe_s2.T_INCIDENCE = 0.0
    oe_s2.T_REFLECTION = 180.0
    oe_s2.T_SOURCE = 7097.5

    # Slit 3
    oe_s3.DUMMY = 0.1
    oe_s3.FWRITE = 3
    oe_s3.F_REFRAC = 2
    oe_s3.F_SCREEN = 1
    oe_s3.I_SLIT = numpy.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
    oe_s3.N_SCREEN = 1
    oe_s3.RX_SLIT = numpy.array([18.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe_s3.RZ_SLIT = numpy.array([10.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    oe_s3.T_IMAGE = 774.0
    oe_s3.T_INCIDENCE = 0.0
    oe_s3.T_REFLECTION = 180.0
    oe_s3.T_SOURCE = -774.0


    """
    Correct ray_tracing order:
    oe1: Toroidal M1
    oe_s2: S2
    oe2: Fictitious Slit 1
    oe3: PGM Mirror
    oe4: Grating
    oe5: Fictitious Slit 2
    oe_s3: S3
    oe6: Spherical M3
    oe7: Exit Slits
    oe8: Spherical M4
    oe9: Ellipsoidal M5
    """

    list_oe = [oe1, oe_s2, oe2, oe3, oe4, oe5, oe_s3, oe6, oe7, oe8, oe9]
    beam.genSource(oe0)    
    return list_oe, beam

def optimize(E: float, delta_E: float, cff: float, order: int)-> float:
    """
    Function to optimize the energy range to simulate for a given energy

    Parameters:
    E: float
        Energy of the beam in eV
    delta_E: float
        Energy range to simulate in eV
    cff: float
        Fixed focus constant of the PGM
    order: int
        Grating order to simulate

    Returns:
    delta_E_prime: float    
        Optimized energy range to simulate in eV
    """

    list_oe, beam = set_up(E, delta_E, cff, order)
    fwhm = trace(list_oe, beam)[0]
    if type(fwhm) == None:
        return 0
    delta_E_prime = fwhm*2
    while numpy.abs(delta_E_prime - delta_E)/delta_E > 0.30:
        delta_E = delta_E_prime
        list_oe, beam = set_up(E, delta_E, cff, order)
        fwhm = trace(list_oe, beam)[0]

        delta_E_prime = fwhm*2
        plt.close()
    return 2*fwhm

def simulate(args):
    """
    Function to simulate the beam through the optical elements and calculate the FWHM of the beam at the exit slit
    Really a wrapper for the multiprocessing pool.
    Parameters:
    args: tuple
        Tuple containing the energy, fixed focus constant, grating order, grating efficiency and flux

    Returns:
    E: float
        Energy of the beam in eV
    fwhm: float
        Full width at half maximum of the beam at the exit slit
    bandwidth: float
        Energy bandwidth of the beam in eV
    flux_calc: float
        Calculated flux of the beam at the end
    intensity: float
        Intensity of the beam at the end
    intensity_dict: dict
        Dictionary of the intensity at each optical element
    height_dict: dict
        Dictionary of the FWHM of the beam at each optical element
    ray_dict: dict
        Dictionary of the number of rays at each optical element
    """
    E, cff, order, grating_eff, flux = args
    #print(f"{E}, {cff}, {order}, {grating_eff}, {flux}")
    delta_E = optimize(E, 0.1, cff, order)
    list_oe, beam = set_up(E, delta_E, cff, order)
    fwhm, intensity, intensity_dict, height_dict, ray_dict = trace(list_oe, beam)
    bandwidth = delta_E / E
    flux_calc = bandwidth/0.001 * flux * grating_eff * intensity/50000
    
    return E, fwhm, bandwidth, flux_calc, intensity, intensity_dict, height_dict, ray_dict


def main():
    flux_E, flux = numpy.loadtxt("./misc/B07_flux_2mradH_0p5mradV_E50eVto15000eV_12Mar2024.dat", unpack=True, skiprows=1)
    # Reading an interpolating the flux calculation
    interpolated_flux = ip.CubicSpline(flux_E, flux)

    # Reading and interpolating the grating efficiency
    order_list, cff_dict, master_dict = initial_read("./misc/B07cN4_grateffs/B07grating2Apr24.json")
    _, cff_dict_l, master_dict_l = initial_read("./misc/B07cN4_grateffs/B07grating15Mar24.json")

    # Scanning over cff_dict read from the grating efficiency file
    for cff in cff_dict[1] + cff_dict_l[1][4:]:
        for order in order_list:

            interpolated_eff = ip.CubicSpline(master_dict[order][cff][0], master_dict[order][cff][1])
            args = [(E, cff, order, interpolated_eff(E), interpolated_flux(E)) for E in numpy.arange(300, order*3000, 10)]
            
            outfile = f"./400lgrating_platinum/cff_{cff:.4f}_order_{order}.csv"

            with Pool(30) as p:
                results = list(tqdm(p.imap(simulate, args),total=len(args)))
            
            with open(outfile, "w") as f:
                writer = csv.writer(f)
                writer.writerow([f"cff = {cff}, order = {order}, {datetime.now()}"])
                writer.writerow(["E", "FWHM", "Bandwidth", "Flux", "Intensity", "Intensity_dict", "Height_dict", "Ray Dict"])
                writer.writerows(results)
            print(f"File {outfile} written")
    #result = simulate((5851, 1.4, 3, interpolated_grating_eff(5851), interpolated_flux(5851)))
    #print(result)

if __name__ == "__main__": 
    main()