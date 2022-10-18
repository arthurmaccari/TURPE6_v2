

# AM: fitted for the French analysis

class Contract():

    def __init__(self, dateStart, dateEnd, tensionDomain):
        self.dateStart = dateStart
        self.dateEnd = dateEnd
        self.tensionDomain = tensionDomain


class Contract_pm(Contract):

    def __init__(self, dateStart, dateEnd, tensionDomain, powConSub, contractType, \
                    tariffOption, elecCons, deltaP, excesses, hasMeter, ownsMeter=None):
        super().__init__(dateStart, dateEnd, tensionDomain)
        self.powConSub = powConSub
        self.contractType = contractType
        self.tariffOption = tariffOption
        self.elecCons = elecCons # 5 slots for France: [HP, HPSH, HCSH, HPSB, HCSB]
        self.deltaP = deltaP # 5 slots for France: [HP, HPSH, HCSH, HPSB, HCSB]
        self.excesses = excesses # for btsup36 CMDPS part
        self.hasMeter = hasMeter # for the CC part of the TURPE6
        self.ownsMeter = ownsMeter
    
    def get_relevant_elec_consumption(self, timespan):
        # AM: arbitrary choice for the "à cheval" cases
        contractTimeSpan = self.dateEnd - self.dateStart
        if contractTimeSpan == timespan:
            return self.elecCons
        _elecCons = self.elecCons
        timeFrac = timespan/contractTimeSpan
        length = len(self.elecCons)
        for i in range(length):
            _elecCons[i] *= timeFrac
        return _elecCons
    
    def get_addPowNoExcess(self):
        pass


class Contract_ps(Contract):

    def __init__(self, dateStart, dateEnd, tensionDomain, hasItsOwnCell, connectionType):
        super().__init__(dateStart, dateEnd, tensionDomain)
        self.hasItsOwnCell = hasItsOwnCell # {True, False}
        self.connectionType = connectionType # {"aerial", "underground"}


class Contract_pe(Contract):

    def __init__(self, dateStart, dateEnd, tensionDomain, powConSub, hasItsOwnCell, 
                    hasMeterForActiveDeltaP, elecCons, connectionType, 
                    connectedToTransformerDifferentFromMain, 
                    connectedToCellOnlySupplyingEmergency):
        super().__init__(dateStart, dateEnd, tensionDomain)
        self.powConSub = powConSub
        self.hasItsOwnCell = hasItsOwnCell
        self.hasMeterForActiveDeltaP = hasMeterForActiveDeltaP
        self.elecCons = elecCons # int
        self.connectionType = connectionType
        self.cellDifferentFromMain = connectedToTransformerDifferentFromMain
        self.cellOnlySupplyingEmergency = connectedToCellOnlySupplyingEmergency