
import sys
sys.path.insert(0, "C:\\Users\\arthur.maccari\\Desktop\\TURPE6_gits\\TURPE6_v2")

from Parsers import parse_yml_file

import numpy as np
import datetime as dt
import calendar as cal


def get_relevant_dates(contract, year): # in hours
    date = dt.date(year,1,1)
    if contract.dateStart < year:
        return date, contract.dateEnd
    if contract.dateEnd > year:
        return contract.dateStart, date + dt.timedelta(365 + cal.isleap(year))
    return contract.dateStart, contract.dateEnd

def compute_turpe_bt(client, year): #AM: lacks CER part for btsup36

    def get_turpe_object(tensionDomain):
        file_path = "_1_Params/France/Turpe/Turpe_" + tensionDomain + ".yml"
        return parse_yml_file(file_path)["turpe_" + tensionDomain]

    params = {
        "btinf36": get_turpe_object("btinf36"),
        "btsup36": get_turpe_object("btsup36"),
        "hta1": get_turpe_object("hta1"),
        "hta2": get_turpe_object("hta2"),
        "htb1": get_turpe_object("htb1"),
        "htb2": get_turpe_object("htb2"),
        "htb3": get_turpe_object("htb3")
    }

    turpe = 0
    contracts_pm = client.get_contracts("pm", year)

    def get_CG_part(contract, timeFrac):
        nonlocal params
        return params["CG"][contract.contType]*timeFrac

    def get_CI_part(contract): #AM: verify elecCons
        nonlocal params
        return params[contract.tensionDomain]["CI"]*sum(contract.elecCons)/1000 # /1000 because coeff in €/MWh
    
    def get_CC_part(contract, timeFrac):
        nonlocal params
        if contract.hasMeter:
            return params[contract.tensionDomain]["CC"]["with_meter"]*timeFrac
        return params[contract.tensionDomain]["CC"]["without_meter"]*timeFrac
    
    def compute_CS_part(contract, timeFrac, relTimeSpan):
        
        nonlocal params

        b = params[contract.tensionDomain]["CS"][contract.tariffOption]["b"]
        c = params[contract.tensionDomain]["CS"][contract.tariffOption]["c"]
        
        cs = 0
        length = len(b)
        powConSub = contract.powConSub
        elecCons = contract.get_relevant_elec_consumption(relTimeSpan)
        if contract.tensionDomain == "btinf36":
            cs = b*powConSub
            for i in range(length):
                cs += c[i]*elecCons[i]
        else:
            cs = b[0]*powConSub[0] + c[0]*elecCons[0]
            for i in range(1,length):
                cs += b[i]*(powConSub[i]-powConSub[i-1])
                cs += c[i]*elecCons[i]
        
        return cs*timeFrac
    
    def compute_CMDPS_part(contract, turpe, relStartDate, relEndDate): # only for btsup36, to compute last
        
        nonlocal params
        
        alpha = params[contract.tensionDomain]["CMDPS"]["alpha"]
        cmdps = 0
        
        _relStartDate = dt.datetime.strptime(relStartDate, "%Y-%m-%d") #AM: verify is truly needed
        _relEndDate = dt.datetime.strptime(relEndDate, "%Y-%m-%d") #AM: verify is truly needed
        startDay = _relStartDate.day
        startMonth = _relStartDate.month
        endDay = _relEndDate.month
        endMonth = _relEndDate.month
        daysInLastMonth = cal.monthrange(_relEndDate.year, endMonth)[1]
        daysInFirstMonth = cal.monthrange(_relStartDate.year, startMonth)[1]
        totalNbDays = (relEndDate - relStartDate).days
        
        startBit = 0
        nbMonths = 0
        endBit = 0
        
        #AM: start/end hours not considered, assumption here
        if startMonth == endMonth:
            pass # just not to forget the case was taken into account
        else:
            if startDay == 1:
                if daysInLastMonth == endDay:
                    nbMonths = endMonth - startMonth + 1
                else:
                    nbMonths = endMonth - startMonth
                    endBit = endDay/totalNbDays
            else:
                startBit = (daysInFirstMonth - startDay + 1)/totalNbDays
                if daysInLastMonth == endDay:
                    nbMonths = endMonth - startMonth
                else:
                    nbMonths = endMonth - startMonth - 1
                    endBit = endDay/totalNbDays

        if nbMonths == 0:
            h = sum(contract.excesses[startMonth])
            cmdpsMonth = alpha*h
            check1 = .3*(turpe + cmdpsMonth)
            check2 = 25*contract.get_addPowNoExcess()*powTariff #AM: WIP
            if cmdpsMonth > check1 and cmdpsMonth > check2:
                cmdps += max(check1, check2)
            else:
                cmdps += cmdpsMonth
            return cmdps
        
        # nbMonths != 0
        if startBit == 0:
            h = sum(contract.excesses[endMonth])
            cmdpsMonth = alpha*h
            check1 = .3*(turpe*endBit + cmdpsMonth)
            check2 = 25*contract.get_addPowNoExcess()*powTariff #AM: WIP
            if cmdpsMonth > check1 and cmdpsMonth > check2:
                cmdps += max(check1, check2)
            else:
                cmdps += cmdpsMonth
        
        if endBit == 0:
            h = sum(contract.excesses[startMonth])
            cmdpsMonth = alpha*h
            check1 = .3*(turpe*startBit + cmdpsMonth)
            check2 = 25*contract.get_addPowNoExcess()*powTariff #AM: WIP
            if cmdpsMonth > check1 and cmdpsMonth > check2:
                cmdps += max(check1, check2)
            else:
                cmdps += cmdpsMonth

        turpeMonth = (turpe - turpe*startBit - turpe*endBit)/nbMonths

        for i in range(nbMonths):
            h = sum(contract.excesses[startMonth + i])
            cmdpsMonth = alpha*h
            check1 = .3*(turpeMonth + cmdpsMonth)
            check2 = 25*contract.get_addPowNoExcess()*powTariff #AM: WIP
            if cmdpsMonth > check1 and cmdpsMonth > check2:
                cmdps += max(check1, check2)
            else:
                cmdps += cmdpsMonth
        
        return cmdps
    
    turpe_contract = 0 # introduced for the CMDPS of btsup36, otherwise useless
    
    for contract in contracts_pm:

        relStartDate, relEndDate = get_relevant_dates(contract, year)
        relTimeSpan = relEndDate - relStartDate
        timeFrac = relTimeSpan/(dt.date(year,1,1) + dt.timedelta(365 + cal.isleap(year)))
        
        turpe_contract += get_CG_part(contract, timeFrac)
        turpe_contract += get_CI_part(contract)
        turpe_contract += get_CC_part(contract, timeFrac)
        turpe_contract += compute_CS_part(contract, timeFrac, relTimeSpan)
        if contract.tensionDomain == "btsup36":
            turpe_contract += compute_CMDPS_part(contract, turpe_contract, relStartDate, relEndDate)
        turpe += turpe_contract
    
    return turpe


























def compute_turpe(client, date):
    """
    Computes the TURPE paid by the household for the given year.

    :type client:           Client
    :content client:        The considered client.

    :type date:             dt.date
    :content date:          The date of the first day of the considered year.
    """

    contracts_pm = client.get_contracts("pm", date)
    contracts_ps = client.get_contracts("ps", date)
    contracts_pe = client.get_contracts("pe", date)

    turpe = 0

    def get_turpe_object(tensionDomain):
        file_path = "_1_Params/France/Turpe/Turpe_" + tensionDomain + ".yml"
        return parse_yml_file(file_path)["turpe_" + tensionDomain]

    params = {
        "btinf36": get_turpe_object("btinf36"),
        "btsup36": get_turpe_object("btsup36"),
        "hta1": get_turpe_object("hta1"),
        "hta2": get_turpe_object("hta2"),
        "htb1": get_turpe_object("htb1"),
        "htb2": get_turpe_object("htb2"),
        "htb3": get_turpe_object("htb3")
    }

    def get_relevant_timespan(contract, date): # in hours
        if contract.dateStart < date.year:
            return contract.dateEnd - date
        if contract.dateEnd > date.year:
            return date + dt.timedelta(365) - contract.dateStart # AM: need to control for leap years
        return contract.dateEnd - contract.dateStart
    
    #relTimeSpan = get_relevant_timespan(contract, date)

    def get_relevant_elec_consumption(contract, timespan):
        # AM: arbitrary choice for the "à cheval" cases
        contractTimeSpan = contract.dateEnd - contract.dateStart
        if contractTimeSpan == timespan:
            return contract.elecCons
        elecCons = contract.elecCons
        timeFrac = timespan/contractTimeSpan
        length = len(elecCons)
        for i in range(length):
            elecCons[i] *= timeFrac
        return elecCons
    
    # timeFrac = relTimeSpan/(date + dt.timedelta(365)) # AM: need to control for leap years

    def get_CG_part(contract, timeFrac):
        nonlocal params
        if contract.tensionDomain[:-1] == "htb":
            return params[contract.tensionDomain]["CG"]["a"]*timeFrac
        return params["CG"][contract.contType]*timeFrac
    
    #elecCons = get_relevant_elec_consumption(contract, relTimeSpan)
    
    def get_CI_part(tensionDomain, elecCons):
        nonlocal params
        return params[tensionDomain]["CI"]*sum(elecCons)/1000 # /1000 because coeff in €/MWh
    
    def get_CC_part(contract, timeFrac): # AM: verify for HTA and BT
        nonlocal params
        if contract.tensionDomain[:-1] == "htb":
            if contract.hasMeter:
                return params[contract.tensionDomain]["CC"]["detenteur_compteur"]["utilisateur"]*timeFrac
            else:
                return params[contract.tensionDomain]["CC"]["detenteur_compteur"]["gestionnaire"]*timeFrac
        return params[contract.tensionDomain]["CC"]*timeFrac
    
    def compute_CS_part(contract, elecCons, timeFrac):

        nonlocal params

        if contract.tensionDomain == "htb3":
            c = params[contract.tensionDomain]["CS"]["c"]
            return c*sum(elecCons)*timeFrac

        # the b coefficients
        b = params[contract.tensionDomain]["CS"][contract.tariffOption]["b"]

        # the c coefficients
        c = params[contract.tensionDomain]["CS"][contract.tariffOption]["c"]
        
        cs = 0
        length = len(b)
        powConSub = contract.powConSub
        if contract.tensionDomain == "btinf36":
            cs = b*powConSub
            for i in range(length):
                cs += c[i]*elecCons[i]
        else:
            cs = b[0]*powConSub[0] + c[0]*elecCons[0]
            for i in range(1,length):
                cs += b[i]*(powConSub[i]-powConSub[i-1])
                cs += c[i]*elecCons[i]
        
        return cs*timeFrac
    
    def compute_CR_part(contract):

        nonlocal params
        
        if contract.tensionDomain == "BT" or not contract.opted_for_CR:
            return 0
        
        if contract.tensionDomain == "HTB3": # AM: WIP
            return params["CR"]["k"]*contract.l*contract.maxPowCon
        
        # the regrouped power connection subscription
        b = params["CS"][contract.tariffOption]["b"]
        length = len(b)
        powConSub = contract.powConSub
        powConSubRegrouped = powConSub[0]
        for i in range(1,length):
            powConSubRegrouped += b[i]/b[0]*(powConSub[i]-powConSub[i-1])
        coeffAerial = params["CR"]["liaisons"]["aeriennes"]
        coeffUnderground = params["CR"]["liaisons"]["souterraines"]

        # the L*k part
        l = coeffAerial*contract.lAerial + coeffUnderground*contract.lUnderground

        return l*powConSubRegrouped
    
    def compute_CACS_part(household):

        nonlocal params

        # the fixed fee
        fixedFee = 0
        cs = 0
        
        for comp in household.complementaryPowSupply:
            if comp.ownsCell:
                fixedFee += params["CACS"]["cellules"]
            if comp.tensionDomain == "HTB3":
                coeffL = params["CACS"]["liaisons"]
                fixedFee += coeffL*comp.l
            else:
                coeffAerial = params["CACS"]["liaisons"]["aeriennes"]
                coeffUnderground = params["CACS"]["liaisons"]["souterraines"]
                fixedFee += coeffAerial*household.contract.lAerial + coeffUnderground*household.contract.lUnderground
        
        for emer in household.emergencyPowSupply:
            if emer.ownsCell:
                fixedFee += params["CACS"]["cellules"]
            if comp.tensionDomain == "HTB3":
                coeffL = params["CACS"]["liaisons"]
                fixedFee += coeffL*comp.l
            else:
                coeffAerial = params["CACS"]["liaisons"]["aeriennes"]
                coeffUnderground = params["CACS"]["liaisons"]["souterraines"]
                fixedFee += coeffAerial*household.contract.lAerial + coeffUnderground*household.contract.lUnderground
            
            # emergency CS if different domains of tension
            if emer.tensionDomain != household.contract.tensionDomain and emer.hasOverflowMeter:
                coeff1 = params["CACS"]["alim_secours"][emer.tensionDomain]["prime_fixe"]
                coeff2 = params["CACS"]["alim_secours"][emer.tensionDomain]["part_energie"]
                coeff3 = params["CACS"]["alim_secours"][emer.tensionDomain]["alpha"]
                for i in range(12):
                    cs += coeff1*emer.powConSub[i] + coeff2*emer.elecCons[i] + coeff3*np.sqrt(lambda x:x*x, emer.deltaPowerEmergency[i])




    """
      CG.a:                       €/contrat/an
      CI:                         €/MWh
      CC:                         €/an
      CS.b:                       €/kW/an
      CS.c:                       €/kWh
      CR.liaisons:                €/kW/km/an
      CACS.cellules:              €/cellule/an
      CACS.liaisons:              €/km/an
      CACS.reservation_puissance: €/kW/an ou €/kVA/an
      CACS.prime_fixe:            €/kW/an
      CACS.part_energie:          €/kWh
      CACS.alpha:                 €/kW
      CDPP.alpha:                 N/A
    """