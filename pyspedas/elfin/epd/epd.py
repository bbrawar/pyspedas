import logging
from pytplot import get_data
import numpy as np

from pyspedas.elfin.load import load
from pyspedas.elfin.epd.postprocessing import epd_l1_postprocessing, epd_l2_postprocessing

def elfin_load_epd(trange=['2020-11-01', '2020-11-02'],
        probe='a',
        datatype='pef',
        level='l1',
        type_='nflux',
        get_support_data=False,
        varformat=None,
        varnames=[],
        downloadonly=False,
        notplot=False,
        no_update=False,
        time_clip=True,
        nspinsinsum=None,
        fullspin=False,
        PAspec_energies=None,
        PAspec_energybins=None,
        Espec_LCfatol=None,
        Espec_LCfptol=None,
):
    """
    This function loads data from the Energetic Particle Detector (EPD) and process L1 and L2 data.

    Parameters for Load Routine
    ----------
        trange : list of str
            Time range of interest [starttime, endtime]. Format can be
            ['YYYY-MM-DD','YYYY-MM-DD'] or ['YYYY-MM-DD/hh:mm:ss','YYYY-MM-DD/hh:mm:ss']

        probe: str, optional
            Spacecraft identifier. Options are 'a' (default) and 'b'.

        level: str, optional.
            Data level. Options are 'l1' (default) and 'l2'.

        get_support_data: bool, optional
            If True, data with an attribute "VAR_TYPE" with a value of "support_data"
            will be loaded into tplot.  By default, only loads in data with a
            "VAR_TYPE" attribute of "data".

        varformat: str, optional
            The file variable formats to load into tplot.  Wildcard character
            "*" is accepted. By default, all variables are loaded in.

        varnames: list of str, optional
            List of variable names to load. By default, all data variables are loaded.

        downloadonly: bool, optional
            If True, only downloads the CDF files without loading them into tplot variables. 
            Default is False.

        notplot: bool, optional
            If True, returns data in hash tables instead of creating tplot variables. 
            Default is False.

        no_update: bool
            If True, loads data only from the local cache. Default is False. 

        time_clip: bool
            If True, clips the variables to the exact range specified in the trange. 
            Default is True.

    Parameters for L1 data
    ----------
        datatype: str, optional. 
            Data type of L1 data. Options are 'pef' (default), 'pif', 'pes', 'pis'. 

        type_ : str, optional
            Calibrated data type of L1 data. Options are 'raw', 'cps', 'nflux' (default), 'eflux'.

        nspinsinsum: int, optional
            Number of spins in sum which is needed by the L1 calibration function.
    
    Parameters for L2 data
    ----------
        fullspin: bool, optional.
            If True, generate L2 full spin spectrogram. By default, L2 half spin spectrogram is generated.

        PAspec_energybins: list of tuple of int, optional
            Specified the energy bins used for generating L2 pitch angle spectrogram. 
            Default is [(0,2),(3,5), (6,8), (9,15)]. If both 'PAspec_energybins' and 'PAspec_energies' 
            are set, 'energybins' takes precedence.
            
        PAspec_energies: list of tuple of float, optional
            Specifies the energy range for each bin in the L2 pitch angle spectrogram.
            Example: energies=[(50.,160.),(160.,345.),(345.,900.),(900.,7000.)]
            If both 'energybins' and 'energies' are set, 'energybins' takes precedence.
            Energy and energybin table:
            channel     energy_range    energy_midbin
            0           50-80           63.2
            1           80-120          97.9
            2           120-160         138.5
            3           160-210         183.3
            4           210-270         238.1
            5           270-345         305.2
            6           345-430         385.1
            7           430-630         520.4
            8           630-900         752.9
            9           900-1300        1081.6
            10          1300-1800       1529.7
            11          1800-2500       2121.3
            12          2500-3350       2893.9
            13          3350-4150       3728.6
            14          4150-5800       4906.1
            15          5800+           6500.0

        Espec_LCfatol: float, optional
            Tolerance angle for para and anti flux in generating L2 energy spectrogram. 
            A positive value makes the loss cone/antiloss cone smaller by this amount. 
            Default is 22.25 deg.

        Espec_LCfptol: float, optional
            Tolerance angle for perp flux in generating L2 energy spectrogram. 
            A negative value means a wider angle for perp flux.
            Default is -11 deg.

    Returns
    ----------
        List of tplot variables created.

    """
    logging.info("ELFIN EPD: START LOADING.")
    
    tvars = load(instrument='epd', probe=probe, trange=trange, level=level, datatype=datatype,
                 get_support_data=get_support_data, varformat=varformat, varnames=varnames, downloadonly=downloadonly,
                 notplot=notplot, time_clip=time_clip, no_update=no_update)

    logging.info("ELFIN EPD: LOADING END.")
    if notplot or downloadonly:
        return tvars
    elif not tvars:
        logging.error('ELFIN EPD: cannot load data.')
        return tvars
   
    CALIBRATED_TYPE_UNITS = {
        "raw": "counts/sector",
        "cps": "counts/s",
        "nflux": "#/(s-cm$^2$-str-MeV)",
        "eflux": "keV/(s-cm$^2$-str-MeV)",
    }

    if type_ in ("cal", "calibrated") or type_ not in CALIBRATED_TYPE_UNITS.keys():
        type_ = "nflux"
        
    if level == "l1":
        l1_tvars = epd_l1_postprocessing(tvars, trange=trange, type_=type_, nspinsinsum=nspinsinsum,
                                     unit=CALIBRATED_TYPE_UNITS[type_])
        return l1_tvars

    elif level == "l2":
        logging.info("ELFIN EPD L2: START PROCESSING.")
        # check whether input type is allowed
        if type_ not in ("nflux","eflux"):
            logging.warning(f"fluxtype {type_} is not allowed in l2 data, change to nflux!")
            type_ = "nflux"

        res = 'hs' if fullspin is False else 'fs'

        # if 32 sector data is needed, pass the variables with 32
        tvars_32 = [tvar for tvar in tvars if '_32' in tvar]
        tvars_16 = [tvar.replace('_32', '') for tvar in tvars_32]
        tvars_other = list(set(tvars) - set(tvars_32) - set(tvars_16))
        
        tvars_input = tvars_other + tvars_16
        if len(tvars_32) != 0 :
            data = get_data(tvars_32[0])
            if np.any(~np.isnan(data.y)) : # if any 32 sector data is not nan
                tvars_input = tvars_other + tvars_32
        
        l2_tvars = epd_l2_postprocessing(
            tvars_input,
            fluxtype=type_,
            res=res,
            PAspec_energies=PAspec_energies,
            PAspec_energybins=PAspec_energybins,
            Espec_LCfatol=Espec_LCfatol,
            Espec_LCfptol=Espec_LCfptol,)
        
        return l2_tvars
    else:
        raise ValueError(f"Unknown level: {level}")

    return tvars