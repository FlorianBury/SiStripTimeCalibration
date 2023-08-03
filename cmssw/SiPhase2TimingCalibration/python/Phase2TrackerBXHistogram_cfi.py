import FWCore.ParameterSet.Config as cms

from DQMServices.Core.DQMEDAnalyzer import DQMEDAnalyzer
timeCalib = DQMEDAnalyzer('Phase2TrackerBXHistogram',
    VerbosityLevel = cms.int32(2),
    TopFolderName = cms.string("Ph2TkBXHist"),
    PSimHitSource  = cms.VInputTag('g4SimHits:TrackerHitsPixelBarrelLowTof',
                                   'g4SimHits:TrackerHitsPixelBarrelHighTof',
                                   'g4SimHits:TrackerHitsPixelEndcapLowTof',
                                   'g4SimHits:TrackerHitsPixelEndcapHighTof',
                                   'g4SimHits:TrackerHitsTIBLowTof',
                                   'g4SimHits:TrackerHitsTIBHighTof',
                                   'g4SimHits:TrackerHitsTIDLowTof',
                                   'g4SimHits:TrackerHitsTIDHighTof',
                                   'g4SimHits:TrackerHitsTOBLowTof',
                                   'g4SimHits:TrackerHitsTOBHighTof',
                                   'g4SimHits:TrackerHitsTECLowTof',
                                   'g4SimHits:TrackerHitsTECHighTof',),
    MixPSimHitSource  = cms.VInputTag(
                                   'mix:g4SimHitsTrackerHitsPixelBarrelLowTof',
                                   'mix:g4SimHitsTrackerHitsPixelBarrelHighTof',
                                   'mix:g4SimHitsTrackerHitsPixelEndcapLowTof',
                                   'mix:g4SimHitsTrackerHitsPixelEndcapHighTof',
                                   'mix:g4SimHitsTrackerHitsTIBLowTof',
                                   'mix:g4SimHitsTrackerHitsTIBHighTof',
                                   'mix:g4SimHitsTrackerHitsTIDLowTof',
                                   'mix:g4SimHitsTrackerHitsTIDHighTof',
                                   'mix:g4SimHitsTrackerHitsTOBLowTof',
                                   'mix:g4SimHitsTrackerHitsTOBHighTof',
                                   'mix:g4SimHitsTrackerHitsTECLowTof',
                                   'mix:g4SimHitsTrackerHitsTECHighTof'),
    UseMixing = cms.bool(True),
    TrackingTruthSource = cms.InputTag( "mix:MergedTrackTruth" ),
    SimTrackSource = cms.InputTag("g4SimHits"),
    GeometryType = cms.string('idealForDigi'),
    Mode = cms.string("scan"),
    Subdetector = cms.string("ALL"),
    PulseShapeParameters = cms.vdouble(-3.0, 16.043703, 99.999857, 40.571650, 2.0, 1.2459094),
    BXRange = cms.int32(5),
    CBCDeadTime = cms.double(2.7),
    PTCut = cms.double(2.),
    TofUpperCut = cms.double(12.5),
    TofLowerCut = cms.double(-12.5),
    OffsetMin  = cms.double(0.),
    OffsetMax  = cms.double(50.),
    OffsetStep = cms.double(0.1),
    OffsetEmulate = cms.double(0.),
    ThresholdInElectrons_Barrel = cms.double(6300.),
    ThresholdInElectrons_Endcap = cms.double(6300.),
    ThresholdSmearing_Barrel = cms.double(0.),
    ThresholdSmearing_Endcap = cms.double(0.),
    TOFSmearing = cms.double(0.),
)

from Configuration.ProcessModifiers.premix_stage2_cff import premix_stage2
premix_stage2.toModify(timeCalib,
    OuterTrackerDigiSimLinkSource = "mixData:Phase2OTDigiSimLink",
    InnerPixelDigiSimLinkSource = "mixData:PixelDigiSimLink",
)

# For phase2 premixing switch the sim digi collections to the ones including pileup
#from Configuration.Eras.Modifier_phase2_tracker_cff import phase2_tracker
#from Configuration.ProcessModifiers.premix_stage2_cff import premix_stage2
#premix_stage2.toModify(timeCalib,
#    TrackingTruthSource = "mixData:MergedTrackTruth",
#    UseMixing = cms.bool(True),
#)
