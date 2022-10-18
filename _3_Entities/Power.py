

class Power():

    def __init__(self, regroupId=None):
        self.contracts = []
        self.regroupId = regroupId
    
    def add_contract(self, contract):
        self.contracts.append(contract)