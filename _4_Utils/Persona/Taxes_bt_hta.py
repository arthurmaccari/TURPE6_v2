
import sys
sys.path.insert(0, "C:\\Users\\arthur.maccari\\Desktop\\TURPE6_gits\\TURPE6_v3")

from _4_Utils.Parsers import parse_yml_file


def get_turpe_object(tensionDomain):
        file_path = "_1_Params/Turpe/Turpe_" + tensionDomain + ".yml"
        return parse_yml_file(file_path)["turpe_" + tensionDomain]

def compute_turpe_btinf36(client):

    params = {
        "btinf36": get_turpe_object("btinf36"),
        "btsup36": get_turpe_object("btsup36"),
        "hta": get_turpe_object("hta")
    }

    turpe = 0
    contracts_pm = client.contracts["pm"]

    def get_CG_part(contract):
        nonlocal params
        if client.consumerType == "autoprod_indiv_avec_inj":
            return params[contract.tensionDomain]["CG"][client.consumerType]
        return params[contract.tensionDomain]["CG"][client.consumerType][contract.contractType]

    def get_CI_part(contract): #AM: verify elecCons
        nonlocal params
        return params[contract.tensionDomain]["CI"]*sum(contract.elecCons)/1000 # /1000 because coeff in €/MWh
    
    def get_CC_part(contract):
        nonlocal params
        if contract.hasMeter:
            return params[contract.tensionDomain]["CC"]["avec_disp_de_comptage"]
        return params[contract.tensionDomain]["CC"]["sans_disp_de_comptage"]
    
    def compute_CS_part(contract):
        
        nonlocal params

        b = params[contract.tensionDomain]["CS"][contract.tariffOption]["b"]
        if contract.tariffOption == "CU4_autoprod_collective" or contract.tariffOption == "MU4_autoprod_collective" or contract.tariffOption == "LU4_autoprod_collective":
            cAlloproduit = params[contract.tensionDomain]["CS"][contract.tariffOption]["c"]["alloproduit"]
            cAutoproduit = params[contract.tensionDomain]["CS"][contract.tariffOption]["c"]["autoproduit"]
            c = cAlloproduit + cAutoproduit
        else:
            c = params[contract.tensionDomain]["CS"][contract.tariffOption]["c"]
        
        powConSub = contract.powConSub
        lengthC = len(c)

        if contract.tensionDomain == "btinf36":
            cs = b*powConSub
            for i in range(lengthC):
                cs += c[i]*contract.elecCons[i]
            return cs

        lengthB = len(b)
        cs = b[0]*powConSub[0]
        for i in range(1,lengthB):
            cs += b[i]*(powConSub[i]-powConSub[i-1])
        for j in range(lengthC):
            cs += c[j]*contract.elecCons[j]
        return cs
    
    for contract in contracts_pm:
        turpe += get_CG_part(contract)
        turpe += get_CI_part(contract)
        turpe += get_CC_part(contract)
        turpe += compute_CS_part(contract)

        print("CG: ", get_CG_part(contract))
        print("CI: ", get_CI_part(contract))
        print("CC: ", get_CC_part(contract))
        print("CS: ", compute_CS_part(contract))
    
    return turpe



# Looping through all possibilities to see if everything is working correctly

from _3_Entities.Client import Client
from _3_Entities.Contract import Contract_pm

for tensionDomain in ["btinf36", "btsup36", "hta"]:
    
    if tensionDomain == "hta":
        ct = ["consommateur", "autoprod_indiv_avec_inj", "autoprod_indiv_sans_inj"]
    else:
        ct = ["consommateur", "autoprod_indiv_avec_inj", "autoprod_indiv_sans_inj", "autoprod_collectif"]

    for consumerType in ct:
        for contractType in ["CARD", "contrat_unique"]:

            if tensionDomain == "btinf36":
                powConSub = 9 # for tests
                if consumerType == "consommateur":
                    elecCons = [6640+106,7760+45,1680+147,2040+67] # for tests
                    to = ["CU4","CU","MU4","MUDT","LU"]
                else:
                    elecCons = [6640+106,7760+45,1680+147,2040+67,0,0,0,0] # for tests
                    to = ["CU4","CU","MU4","MUDT","LU","CU4_autoprod_collective","MU4_autoprod_collective"]
            
            elif tensionDomain == "btsup36":
                powConSub = [37,38,39,40] # for tests
                if consumerType == "consommateur":
                    elecCons = [6640+106,7760+45,1680+147,2040+67] # for tests
                    to = ["CU4","LU4"]
                else:
                    elecCons = [6640+106,7760+45,1680+147,2040+67,0,0,0,0] # for tests
                    to = ["CU4","LU4","CU4_autoprod_collective","LU4_autoprod_collective"]
            
            elif tensionDomain == "hta":
                powConSub = [37,38,39,40,41] # for tests + not the good domain
                elecCons = [6640+106,7760+45,1680+147,2040+67,0] # for tests
                to = ["CU_pointe_fixe","CU_pointe_mobile","LU_pointe_fixe","LU_pointe_mobile"]

            for tariffOption in to:
                for hasMeter in [True, False]:
                    contract = Contract_pm(None, None, tensionDomain, powConSub, contractType, tariffOption, elecCons, None, None, hasMeter)
                    client = Client(consumerType)
                    client.add_contract("pm", contract)
                    print("consumerType : ", consumerType)
                    print("tensionDomain : ", tensionDomain)
                    print("contractType : ", contractType)
                    print("tariffOption : ", tariffOption)
                    print("hasMeter : ", hasMeter)
                    print(compute_turpe_btinf36(client))
                    print("-------")