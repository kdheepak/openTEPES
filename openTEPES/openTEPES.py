"""
Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - March 31, 2023
"""

import time
import os
import setuptools

from pyomo.environ import ConcreteModel, Set

from .openTEPES_InputData        import InputData, SettingUpVariables
from .openTEPES_ModelFormulation import TotalObjectiveFunction, InvestmentModelFormulation, GenerationOperationModelFormulationObjFunct, GenerationOperationModelFormulationInvestment, GenerationOperationModelFormulationDemand, GenerationOperationModelFormulationStorage, GenerationOperationModelFormulationCommitment, GenerationOperationModelFormulationRampMinTime, NetworkSwitchingModelFormulation, NetworkOperationModelFormulation
from .openTEPES_ProblemSolving   import ProblemSolving
from .openTEPES_OutputResults    import InvestmentResults, GenerationOperationResults, ESSOperationResults, FlexibilityResults, NetworkOperationResults, MarginalResults, OperationSummaryResults, ReliabilityResults, CostSummaryResults, EconomicResults, NetworkMapResults


def openTEPES_run(DirName, CaseName, SolverName, pIndOutputResults, pIndLogConsole):

    InitialTime = time.time()
    _path = os.path.join(DirName, CaseName)

    #%% replacing string values by numerical values
    idxDict        = dict()
    idxDict[0    ] = 0
    idxDict[0.0  ] = 0
    idxDict[0.0  ] = 0
    idxDict['No' ] = 0
    idxDict['NO' ] = 0
    idxDict['no' ] = 0
    idxDict['N'  ] = 0
    idxDict['n'  ] = 0
    idxDict['Yes'] = 1
    idxDict['YES'] = 1
    idxDict['yes'] = 1
    idxDict['Y'  ] = 1
    idxDict['y'  ] = 1

    #%% model declaration
    mTEPES = ConcreteModel('Open Generation, Storage, and Transmission Operation and Expansion Planning Model with RES and ESS (openTEPES) - Version 4.11.1 - March 31, 2023')

    pIndOutputResults = [j for i,j in idxDict.items() if i == pIndOutputResults][0]
    pIndLogConsole    = [j for i,j in idxDict.items() if i == pIndLogConsole   ][0]

    # Define sets and parameters
    InputData(DirName, CaseName, mTEPES, pIndLogConsole)

    # Define variables
    SettingUpVariables(mTEPES, mTEPES)

    # objective function and investment constraints
    TotalObjectiveFunction    (mTEPES, mTEPES, pIndLogConsole)
    InvestmentModelFormulation(mTEPES, mTEPES, pIndLogConsole)

    # iterative model formulation for each stage of a year
    for p,sc,st in mTEPES.ps*mTEPES.stt:
        # activate only period, scenario, and load levels to formulate
        mTEPES.del_component(mTEPES.st)
        mTEPES.del_component(mTEPES.n )
        mTEPES.del_component(mTEPES.n2)
        mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and st == stt and mTEPES.pStageWeight[stt] and sum(1 for (st,nn) in mTEPES.s2n))
        mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in                              mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)
        mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in                              mTEPES.pDuration         and           (st,nn) in mTEPES.s2n)

        print('Period '+str(p)+', Scenario '+str(sc)+', Stage '+str(st))

        # operation model objective function and constraints by stage
        GenerationOperationModelFormulationObjFunct   (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationInvestment (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationDemand     (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationStorage    (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationCommitment (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        GenerationOperationModelFormulationRampMinTime(mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkSwitchingModelFormulation              (mTEPES, mTEPES, pIndLogConsole, p, sc, st)
        NetworkOperationModelFormulation              (mTEPES, mTEPES, pIndLogConsole, p, sc, st)

        if pIndLogConsole == 1:
            StartTime         = time.time()
            mTEPES.write(_path+'/openTEPES_'+CaseName+'_'+str(p)+'_'+str(sc)+'.lp', io_options={'symbolic_solver_labels': True})
            WritingLPFileTime = time.time() - StartTime
            StartTime         = time.time()
            print('Writing LP file                        ... ', round(WritingLPFileTime), 's')

        if (len(mTEPES.gc) == 0 or (len(mTEPES.gc) > 0 and mTEPES.pIndBinGenInvest() == 2)) and (len(mTEPES.gd) == 0 or (len(mTEPES.gd) > 0 and mTEPES.pIndBinGenRetire() == 2)) and (len(mTEPES.lc) == 0 or (len(mTEPES.lc) > 0 and mTEPES.pIndBinNetInvest() == 2)):
            mTEPES.pPeriodWeight [p] = 1.0
            mTEPES.pScenProb  [p,sc] = 1.0
            mTEPES.pPeriodProb[p,sc] = 1.0
            # there are no expansion decisions, or they are ignored (it is an operation model)
            ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc)
            mTEPES.pPeriodWeight [p] = 0.0
            mTEPES.pScenProb  [p,sc] = 0.0
            mTEPES.pPeriodProb[p,sc] = 0.0
        elif p == mTEPES.pp.last() and sc == mTEPES.scc.last() and st == mTEPES.stt.last():
            # there are investment decisions (it is an expansion and operation model)
            ProblemSolving(DirName, CaseName, SolverName, mTEPES, mTEPES, pIndLogConsole, p, sc)

    mTEPES.del_component(mTEPES.st)
    mTEPES.del_component(mTEPES.n )
    mTEPES.del_component(mTEPES.n2)
    mTEPES.st = Set(initialize=mTEPES.stt, ordered=True, doc='stages',      filter=lambda mTEPES,stt: stt in mTEPES.stt and mTEPES.pStageWeight[stt] and sum(1 for (stt,nn) in mTEPES.s2n))
    mTEPES.n  = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in                mTEPES.pDuration                                              )
    mTEPES.n2 = Set(initialize=mTEPES.nn,  ordered=True, doc='load levels', filter=lambda mTEPES,nn:  nn  in                mTEPES.pDuration                                              )

    for p,sc in mTEPES.ps:
        mTEPES.pPeriodWeight[p] = mTEPES.pScenProb[p,sc] = mTEPES.pPeriodProb[p,sc] = 1.0

    # output results only for every unit (0), only for every technology (1), or for both (2)
    pIndTechnologyOutput = 1

    # output results just for the system (0) or for every area (1). Areas correspond usually to countries
    pIndAreaOutput = 1

    # output plot results
    pIndPlotOutput = 1

    # indicators to control the amount of output results
    if pIndOutputResults == 1:
        pIndInvestmentResults          = 1
        pIndGenerationOperationResults = 1
        pIndESSOperationResults        = 1
        pIndFlexibilityResults         = 1
        pIndReliabilityResults         = 1
        pIndNetworkOperationResults    = 1
        pIndNetworkMapResults          = 1
        pIndOperationSummaryResults    = 1
        pIndCostSummaryResults         = 1
        pIndMarginalResults            = 1
        pIndEconomicResults            = 1
    else:
        pIndInvestmentResults          = 1
        pIndGenerationOperationResults = 1
        pIndESSOperationResults        = 1
        pIndFlexibilityResults         = 0
        pIndReliabilityResults         = 0
        pIndNetworkOperationResults    = 1
        pIndNetworkMapResults          = 0
        pIndOperationSummaryResults    = 1
        pIndCostSummaryResults         = 0
        pIndMarginalResults            = 0
        pIndEconomicResults            = 0

    if pIndInvestmentResults          == 1:
        InvestmentResults         (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput,                 pIndPlotOutput)
    if pIndGenerationOperationResults == 1:
        GenerationOperationResults(DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndESSOperationResults        == 1:
        ESSOperationResults       (DirName, CaseName, mTEPES, mTEPES, pIndTechnologyOutput, pIndAreaOutput, pIndPlotOutput)
    if pIndFlexibilityResults         == 1:
        FlexibilityResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndReliabilityResults         == 1:
        ReliabilityResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkOperationResults    == 1:
        NetworkOperationResults   (DirName, CaseName, mTEPES, mTEPES)
    if pIndNetworkMapResults          == 1:
        NetworkMapResults         (DirName, CaseName, mTEPES, mTEPES)
    if pIndOperationSummaryResults    == 1:
        OperationSummaryResults   (DirName, CaseName, mTEPES, mTEPES)
    if pIndCostSummaryResults         == 1:
        CostSummaryResults        (DirName, CaseName, mTEPES, mTEPES)
    if pIndMarginalResults            == 1:
        MarginalResults           (DirName, CaseName, mTEPES, mTEPES,                 pIndPlotOutput)
    if pIndEconomicResults            == 1:
        EconomicResults           (DirName, CaseName, mTEPES, mTEPES, pIndAreaOutput, pIndPlotOutput)

    TotalTime = time.time() - InitialTime
    print('Total time                             ... ', round(TotalTime), 's')

    return mTEPES
