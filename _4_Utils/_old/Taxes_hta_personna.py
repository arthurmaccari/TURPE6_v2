
import sys
sys.path.insert(0, "C:\\Users\\arthur.maccari\\Desktop\\TURPE6_gits\\TURPE6_v2")

import numpy as np

from Parsers import parse_yml_file


def get_turpe_object(tensionDomain):
        file_path = "_1_Params/Turpe/Turpe_" + tensionDomain + ".yml"
        return parse_yml_file(file_path)["turpe_" + tensionDomain]

def compute_turpe_btinf36(client):

    params = get_turpe_object("hta")

    turpe = 0
    contracts_pm = client.contracts["pm"]
    contracts_ps = client.contracts["ps"]
    contracts_pe = client.contracts["pe"]

    def get_CG_part(contract):
        nonlocal params
        return params["CG"][contract.contType]

    def get_CI_part(contract): #AM: verify elecCons
        nonlocal params
        return params["CI"]*sum(contract.elecCons)/1000 # /1000 because coeff in €/MWh
    
    def get_CC_part(contract):
        nonlocal params
        if contract.hasMeter:
            return params["CC"]["avec_disp_de_comptage"]
        return params["CC"]["sans_disp_de_comptage"]
    
    def compute_CS_part(contract):
        
        nonlocal params

        b = params["CS"][contract.tariffOption]["b"]
        c = params["CS"][contract.tariffOption]["c"]
        
        cs = 0
        length_b = len(b)
        length_c = len(c)
        powConSub = contract.powConSub
        cs = b[0]*powConSub[0]
        for i in range(1,length_b):
            cs += b[i]*(powConSub[i]-powConSub[i-1])
        for j in range(length_c):
            cs += c[j]*contract.elecCons[j]
        
        return cs
    
    def compute_CMDPS_part(contract):
        
        nonlocal params
        
        b = params["CS"][contract.tariffOption]["b"]
        cmdps = 0
        
        length = len(b)
        for i in range(12):
            for j in range(length):
                cmdps += .04*b[j]*np.sqrt(sum(lambda x:x*x, contract.excesses[i]))
        
        return cmdps
    
    def compute_ps_CACS_part(contract):

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
    
    def compute_CACS_part(contract):

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

    for contract in contracts_pm:
        turpe += get_CG_part(contract)
        turpe += get_CI_part(contract)
        turpe += get_CC_part(contract)
        turpe += compute_CS_part(contract)
        turpe += compute_CMDPS_part(contract)

        print("CG: ", get_CG_part(contract))
        print("CI: ", get_CI_part(contract))
        print("CC: ", get_CC_part(contract))
        print("CS: ", compute_CS_part(contract))
        print("CMDPS: ", compute_CMDPS_part(contract))
        print("-------------")
    
    for contract in contracts_ps: #AM: other part to include for supplemental power contracts?
        turpe += compute_CACS_part(contract)

        print("CACS: ", compute_CACS_part(contract))
        print("-------------")
    
    for contract in contracts_pe:
        turpe += compute_CACS_part(contract)

        print("CACS: ", compute_CACS_part(contract))
        print("-------------")
    
    return turpe


from _3_Entities.Client import Client
from _3_Entities.Contract import Contract_pm

contract = Contract_pm(None, None, "btsup36", 40, "CARD", "LU", 
                    [6640+106,7760+45,1680+147,2040+67], None, None, True)
client = Client("consommateur")
client.add_contract("pm", contract)

print(compute_turpe_btinf36(client))