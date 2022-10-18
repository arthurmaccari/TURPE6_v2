

# AM: fitted for the French analysis

class Client():

    def __init__(self, consumerType):
        self.consumerType = consumerType
        self.contracts = {
            "pm": [], # main power
            "ps": [], # supplemental power
            "pe": []  # emergency power
        }
    
    def add_contract(self, powerType, contract):
        self.contracts[powerType].append(contract)
    
    def get_contracts(self, powerType, year):
        contracts = []
        for cont in self.contracts[powerType]:
            if cont.dateStart.year == year or cont.dateEnd.year == year:
                contracts.append(cont)
        return contracts