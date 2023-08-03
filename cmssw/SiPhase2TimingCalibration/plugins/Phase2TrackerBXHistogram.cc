// -*- C++ -*-
//
// Package:    Phase2TrackerBXHistogram
// Class:      Phase2TrackerBXHistogram
// 
/**\class Phase2TrackerBXHistogram Phase2TrackerBXHistogram.cc 

Description: Test pixel digis. 

*/
//
// Author: Suchandra Dutta, Suvankar Roy Chowdhury, Subir Sarkar
// Date: January 29, 2016
//
// system include files
#include <memory>
#include <stdexcept>
#include "Phase2TrackerBXHistogram.h"

#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/ESWatcher.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/RandomNumberGenerator.h" 


#include "FWCore/ServiceRegistry/interface/Service.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "FWCore/MessageLogger/interface/MessageLogger.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"

// Geometry
#include "Geometry/Records/interface/TrackerDigiGeometryRecord.h"
#include "Geometry/TrackerNumberingBuilder/interface/GeometricDet.h"
#include "Geometry/TrackerGeometryBuilder/interface/TrackerGeometry.h"
#include "Geometry/CommonDetUnit/interface/GeomDet.h"
#include "Geometry/CommonDetUnit/interface/TrackerGeomDet.h"
//#include "Geometry/TrackerGeometryBuilder/interface/PixelGeomDetUnit.h"
//#include "Geometry/TrackerGeometryBuilder/interface/PixelGeomDetType.h"
//#include "Geometry/TrackerGeometryBuilder/interface/StripGeomDetUnit.h"
//#include "Geometry/TrackerGeometryBuilder/interface/StripGeomDetType.h"

// DataFormats
#include "DataFormats/SiStripDetId/interface/SiStripDetId.h"
#include "DataFormats/SiStripDetId/interface/StripSubdetector.h"
#include "DataFormats/TrackerCommon/interface/TrackerTopology.h"
#include "DataFormats/Phase2TrackerDigi/interface/Phase2TrackerDigi.h"
#include "DataFormats/GeometryCommonDetAlgo/interface/MeasurementPoint.h"

#include "SimDataFormats/Track/interface/SimTrackContainer.h"
#include "SimDataFormats/TrackingHit/interface/PSimHitContainer.h"
#include "SimDataFormats/CrossingFrame/interface/MixCollection.h"

// DQM Histograming
#include "DQMServices/Core/interface/MonitorElement.h"
#include "DQMServices/Core/interface/DQMStore.h"
#include "TF1.h"
#include "TTree.h"

// CLHEP 
#include "CLHEP/Random/RandGaussQ.h"
#include "CLHEP/Random/RandFlat.h"
#include "CLHEP/Units/GlobalSystemOfUnits.h"
#include "CLHEP/Units/GlobalPhysicalConstants.h"

namespace scaling {
    double nFactorial(int n) { return std::tgamma(n + 1); }
    double aScalingConstant(int N, int i) {
        return std::pow(-1, (double)i) * nFactorial(N) * nFactorial(N + 2) /
            (nFactorial(N - i) * nFactorial(N + 2 - i) * nFactorial(i));
    }
}  // namespace



// 
// constructors 
//
Phase2TrackerBXHistogram::Phase2TrackerBXHistogram(const edm::ParameterSet& iConfig) :
    /*
        Constructor 
            - Initialise all config parameters
            - Printout of most important parameters
            - Initialise dimensions
    */
    config_(iConfig),
    geomType_(config_.getParameter<std::string>("GeometryType")),
    simTrackSrc_(config_.getParameter<edm::InputTag>("SimTrackSource")),
    pSimHitSrc_(config_.getParameter<std::vector<edm::InputTag> >("PSimHitSource")),
    pMixSimHitSrc_(config_.getParameter<std::vector<edm::InputTag> >("MixPSimHitSource")),
    tParticleSrc_(config_.getParameter<edm::InputTag>("TrackingTruthSource")),
    tParticleToken_(consumes<std::vector<TrackingParticle> >(tParticleSrc_)),
    simTrackToken_(consumes<edm::SimTrackContainer>(simTrackSrc_)),
    topoToken_(esConsumes<TrackerTopology, TrackerTopologyRcd>()),
    geomToken_(esConsumes<TrackerGeometry, TrackerDigiGeometryRecord>(edm::ESInputTag{"", geomType_})),
    pulseShapeParameters_(config_.getParameter<std::vector<double>>("PulseShapeParameters")),
    use_mixing_(config_.getParameter<bool>("UseMixing")),
    mode_(config_.getParameter<std::string>("Mode")),
    subdet_(config_.getParameter<std::string>("Subdetector")),
    bx_range_(config_.getParameter<int>("BXRange")),
    deadTime_(config_.getParameter<double>("CBCDeadTime")),
    pTCut_(config_.getParameter<double>("PTCut")),
    theTofLowerCut_(config_.getParameter<double>("TofLowerCut")),
    theTofUpperCut_(config_.getParameter<double>("TofUpperCut")),
    offset_min_(config_.getParameter<double>("OffsetMin")),
    offset_max_(config_.getParameter<double>("OffsetMax")),
    offset_step_(config_.getParameter<double>("OffsetStep")),
    offset_emulate_(config_.getParameter<double>("OffsetEmulate")),
    theThresholdInE_Endcap_(config_.getParameter<double>("ThresholdInElectrons_Endcap")),
    theThresholdInE_Barrel_(config_.getParameter<double>("ThresholdInElectrons_Barrel")),
    theThresholdSmearing_Endcap_(config_.getParameter<double>("ThresholdSmearing_Endcap")),
    theThresholdSmearing_Barrel_(config_.getParameter<double>("ThresholdSmearing_Barrel")),
    tof_smearing_(config_.getParameter<double>("TOFSmearing")),
    GeVperElectron(3.61E-09), // 1 electron(3.61eV, 1keV(277e, mod 9/06 d.k.
    verbosity_(config_.getParameter<int>("VerbosityLevel"))
{
    if (use_mixing_){
        for(const auto& itag : pMixSimHitSrc_) 
            mixSimHitTokens_.push_back(std::make_pair(itag,consumes<CrossingFrame<PSimHit>>(itag)));
    }
    else{
        for(const auto& itag : pSimHitSrc_) 
            simHitTokens_.push_back(std::make_pair(itag,consumes< edm::PSimHitContainer >(itag)));
    }


    edm::LogInfo("Phase2TrackerBXHistogram") << ">>> Construct Phase2TrackerBXHistogram ";
    if (verbosity_ > 0){
        std::cout << ">>> Construct Phase2TrackerBXHistogram " <<std::endl;
        std::cout << "Mode                        : "<<mode_<<std::endl;
        std::cout << "Threshold (Barrel)          : "<<theThresholdInE_Barrel_<<std::endl;
        std::cout << "Threshold (Endcap)          : "<<theThresholdInE_Endcap_<<std::endl;
        std::cout << "Threshold Smearing (Endcap) : "<<theThresholdSmearing_Endcap_<<std::endl;
        std::cout << "Threshold Smearing (Barrel) : "<<theThresholdSmearing_Barrel_<<std::endl;
        std::cout << "ToF smearing                : "<<tof_smearing_<<std::endl;
        if (mode_ == "emulate")
            std::cout << "Offset for emulation        : "<<offset_emulate_<<std::endl;
    }
    if (mode_ != "scan" && mode_ != "emulate"){
        throw std::invalid_argument("Mode "+mode_+" not understood");
    }

    if (dims_per_subdet.find(subdet_) == dims_per_subdet.end()) {
        throw std::invalid_argument("Subdetector "+subdet_+" not understood");
    } else {
        dimensions_ = dims_per_subdet[subdet_];
    }


 
}

//
// destructor
//
Phase2TrackerBXHistogram::~Phase2TrackerBXHistogram() {
    /*
        Destructor 
            - do anything here that needs to be done at desctruction time 
              (e.g. close files, deallocate resources etc.)
    */
    edm::LogInfo("Phase2TrackerBXHistogram")<< ">>> Destroy Phase2TrackerBXHistogram ";
    if (verbosity_ > 0)
        std::cout << ">>> Destroy Phase2TrackerBXHistogram " << std::endl;
}
//
// -- DQM Begin Run 
//
void Phase2TrackerBXHistogram::dqmBeginRun(const edm::Run& iRun, const edm::EventSetup& iSetup) {
    /*
        Start DQM run begin
            - Clear vector of delays 
            - Intialise array based on min, max and steps
    */
    edm::LogInfo("Phase2TrackerBXHistogram")<< "Initialize Phase2TrackerBXHistogram ";
    if (verbosity_ > 0)
        std::cout << "Initialize Phase2TrackerBXHistogram " <<std::endl;
    offset_scan_.clear();
    if (mode_ == "scan"){
        double offIt = offset_min_;
        offset_scan_.push_back(offIt);
        while (offIt <= offset_max_){
            offIt += offset_step_;
            offset_scan_.push_back(offIt);
        }
    }
    if (mode_ == "emulate"){
        offset_scan_.push_back(offset_emulate_);
    }
    fireRandom_ = true;
}

//
// -- Analyze
//
void Phase2TrackerBXHistogram::analyze(const edm::Event& iEvent, const edm::EventSetup& iSetup) {
    /*
        Analyse
            - Initialise smearing random variables
            - Initialise edm handles
            - Printout of all track informations
            - Loop over delays -> for each delay run the scan of hits 
    */
    using namespace edm;

    // random generator for smearing 
    Service<RandomNumberGenerator> rng;
    if(!rng.isAvailable()) {
        throw cms::Exception("Configuration")
            << "Phase2TrackerBXHistogram requires the RandomNumberGeneratorService,\n"
            "which is not present in the configuration file. You must add\n"
            "the service in the configuration file or remove the modules that\n"
            "require it.\n";
    }
    CLHEP::HepRandomEngine& eng = rng->getEngine(iEvent.streamID());

    if (fireRandom_){
        smearedThresholdFactors_Endcap_.clear();
        smearedThresholdFactors_Barrel_.clear();
        smearedTofFactors_.clear();

        if (theThresholdSmearing_Endcap_ > 0.){
            smearedThreshold_Endcap_ = std::make_unique<CLHEP::RandFlat>(eng,-theThresholdSmearing_Endcap_,theThresholdSmearing_Endcap_); 
        }
        if (theThresholdSmearing_Barrel_ > 0.){
            smearedThreshold_Barrel_ = std::make_unique<CLHEP::RandFlat>(eng,-theThresholdSmearing_Barrel_,theThresholdSmearing_Barrel_); 
        }
        if (tof_smearing_ > 0.){
            smearedTOF_ = std::make_unique<CLHEP::RandFlat>(eng,-tof_smearing_,tof_smearing_); 
        }
        fireRandom_ = false;
    }
    // Tracker Topology 
    const TrackerTopology* tTopo = &iSetup.getData(topoToken_); 
    const TrackerGeometry* tGeom;

    edm::ESWatcher<TrackerDigiGeometryRecord> theTkDigiGeomWatcher;

    if (theTkDigiGeomWatcher.check(iSetup)) {
        tGeom = &iSetup.getData(geomToken_); 
    }  
    else
        return;

    // Particle containers 
    iEvent.getByToken(tParticleToken_, tParticleHandle_);
    iEvent.getByToken(simTrackToken_, simTrackHandle_);

    if (tParticleHandle_.isValid()) {
        std::cout <<"TrackingParticle handle valid" <<std::endl;
        if (verbosity_>1){
            std::cout << "Loop over TrackingParticle particles"<<std::endl;
            unsigned int ival = 0;
            for (std::vector<TrackingParticle>::const_iterator  iterTPart = tParticleHandle_->begin(); iterTPart != tParticleHandle_->end(); ++iterTPart) {
                std::cout << ival++ << ". BX #" << iterTPart->eventId().bunchCrossing() << " Event # " << iterTPart->eventId().event() << " Track Id " << iterTPart->g4Tracks()[0].trackId() << " PDG Id " << iterTPart->pdgId() << " Momentum "<< iterTPart->p() << " Pt " << iterTPart->pt() <<" Eta "<< iterTPart->eta() << " Phi "<< iterTPart->phi() <<std::endl;

            }
        }
    }
    else{
        std::cout <<"TrackingParticle handle not valid" <<std::endl;
    }

    if (simTrackHandle_.isValid()) { 
        std::cout <<"SimTrack handle valid" <<std::endl;
        if (verbosity_>1){
            std::cout << "Loop over SimTrack particles"<<std::endl;
            for (edm::SimTrackContainer::const_iterator simTrkItr = simTrackHandle_->begin(); simTrkItr != simTrackHandle_->end();    ++simTrkItr) {
                unsigned int ival = 0;
                std::cout << ival++ << ". BX # " << simTrkItr->eventId().bunchCrossing() << " Event # " << simTrkItr->eventId().event() << " Track Id " << simTrkItr->trackId() << " PDG Id " << simTrkItr->type() << " Momentum "<< simTrkItr->momentum().P() << " Pt " << simTrkItr->momentum().Pt() <<" Eta "<< simTrkItr->momentum().Eta() << " Phi "<< simTrkItr->momentum().Phi() <<std::endl;

            }
        }
    }
    else{
        std::cout <<"SimTrack handle not valid" <<std::endl;
    }


    // Delay scan //
    for(std::vector<double>::iterator offset = offset_scan_.begin(); offset != offset_scan_.end(); ++offset) {
        if (verbosity_>0){
            std::cout<<"New offset value "<<*offset<<std::endl;
        }
        pulseShapeParameters_[0] = *offset;
        Phase2TrackerBXHistogram::storeSignalShape();
        if (verbosity_>1){
            std::cout << "Pulse shape params : "<<std::endl;
            for(std::vector<double>::iterator psp = pulseShapeParameters_.begin(); psp != pulseShapeParameters_.end(); ++psp) {
                std::cout<<"   "<<*psp<<std::endl;
            }
            std::cout << "Loop over hit "<<std::endl;
        }

        // SimHitTokens 
        if (!use_mixing_){
            if (verbosity_>1){
                std::cout<<"Running <PSimHitContainer>"<<std::endl;
            }
            for (const auto& itoken : simHitTokens_) {
                edm::Handle<edm::PSimHitContainer> simHitHandle;
                iEvent.getByToken(itoken.second, simHitHandle);
                if (verbosity_>1){
                    std::cout<<"Looking at "<<itoken.first<<std::endl;
                }
                if (!simHitHandle.isValid()){
                    if (verbosity_>1){
                        std::cout<<"Not valid hit handle "<<std::endl;
                    }
                    continue;
                }
                const edm::PSimHitContainer& simHits = (*simHitHandle.product());
                for(edm::PSimHitContainer::const_iterator isim = simHits.begin(); isim != simHits.end(); ++isim){
                    if (verbosity_>1){
                        std::cout<<"-------------------------"<<std::endl;
                    }
                    Phase2TrackerBXHistogram::runSimHit(isim,*offset,tTopo,tGeom);
                }
            }
        }


        // MixSimHitTokens 

        if (use_mixing_){
            if (verbosity_>1){
                std::cout<<"Running MixCollection<PSimHit>"<<std::endl;
            }
            for (const auto& itoken : mixSimHitTokens_) {
                edm::Handle<CrossingFrame<PSimHit> > cf_simhit_H;
                bool found = iEvent.getByToken(itoken.second, cf_simhit_H);
                if (verbosity_>1){
                    std::cout<<"Looking at "<<itoken.first<<std::endl;
                }
                if (!found || !cf_simhit_H.isValid()) {
                    if (verbosity_>1){
                        std::cout<<"Not valid hit handle "<<std::endl;
                    }
                    continue;
                }

                std::unique_ptr<MixCollection<PSimHit> > coll(new MixCollection<PSimHit>(cf_simhit_H.product()));
                for(MixCollection<PSimHit>::iterator isim = coll->begin(); isim != coll->end(); ++isim){
                    if (verbosity_>1){
                        std::cout<<"-------------------------"<<std::endl;
                    }
                    Phase2TrackerBXHistogram::runSimHit(isim,*offset,tTopo,tGeom);
                }
            }
        }
    }

    // Final printout for debug purposes //
    if (verbosity_ > 1){
        for (const std::pair<double, HistModes> &it :  offsetBX_){
            const double offset = it.first;
            HistModes hist_mode = it.second;
            std::cout << "Offset = "<<offset<<" Sampled (Integral="<<hist_mode.Sampled->integral()<<",Mean="<<hist_mode.Sampled->getMean()<<")"<<" Latched (Integral="<<hist_mode.Latched->integral()<<",Mean="<<hist_mode.Latched->getMean()<<")"<<std::endl;
        }

    }
}

//
// -- Hit logic
//
template <typename T>
void Phase2TrackerBXHistogram::runSimHit(T isim,double offset, const TrackerTopology* tTopo,const TrackerGeometry* tGeom){
    /*
        Run on all hits 
            - Check if hit is to be considered
            - Check for each BX whether mode if fired
            - Fill histograms 
    */
    // Check BX //
    const PSimHit& simHit = (*isim);
    int bx_true  = simHit.eventId().bunchCrossing();
    if (bx_true != 0){
        if (verbosity_ > 1)
            std::cout << "Not from the main BX : BX = "<<bx_true<<"-> discarded"<<std::endl;
        return;
    }

    // Check track //
    int tkid = (*isim).trackId();
    if (verbosity_ > 1)
        std::cout << "Track id "<<tkid<<std::endl;
    if (tkid <= 0) return;

    unsigned int rawid = simHit.detUnitId();
    const DetId detId(rawid);
    float tkpt = Phase2TrackerBXHistogram::getSimTrackPt(simHit.eventId(), tkid);
    if (verbosity_>1){
        std::cout<<"New hit on detID "<< detId.rawId() <<" with PT = "<<tkpt<<std::endl;
    }       
    if (detId.det() != DetId::Detector::Tracker){
        std::cout<<"\tNot a tracker hit -> discarded"<<std::endl;
        return;
    }
    if (tkpt < pTCut_){
        if (verbosity_>1){
            std::cout <<"PT "<<tkpt<<" below cut at "<<pTCut_<<" -> dismissed"<<std::endl; 
        }
        return;
    }

    // Check dZ //
    float dZ = (*isim).entryPoint().z() - (*isim).exitPoint().z();  
    if (fabs(dZ) <= 0.01){
        if (verbosity_ > 1){
            std::cout<<"\t|dZ| = "<<dZ<<" -> discarded"<<std::endl;
        }
        // Avoid delta rays 
        // We are using this dZ cutoff to try to reject SimHits coming from  delta rays which has a very short track length.
        return;
    }

    // check if strip //
    if (!isStrip(detId)){
        if (verbosity_ > 1){
            std::cout<<"\tNot a strip hit ("<< rawid <<") -> discarded"<<std::endl;
        }
        return;
    }

    // Layer and geometry //
    int layer = tTopo->getOTLayerNumber(rawid);
    if (verbosity_ > 1){
        std::cout << " rawid " << rawid << " layer " << layer ; // << std::endl;
        if (detId.subdetId() == SiStripDetId::SubDetector::TIB)
            std::cout<<" subdet TIB"<<std::endl;
        if (detId.subdetId() == SiStripDetId::SubDetector::TID)
            std::cout<<" subdet TID"<<std::endl;
        if (detId.subdetId() == SiStripDetId::SubDetector::TOB)
            std::cout<<" subdet TOB"<<std::endl;
        if (detId.subdetId() == SiStripDetId::SubDetector::TEC)
            std::cout<<" subdet TEC"<<std::endl;
    }
    if (layer < 0) return;
    const GeomDet *geomDet = tGeom->idToDet(detId);
    if (!geomDet){
        if (verbosity_>1){
            std::cout<<"\tGeometry not valid"<<std::endl;
        }
        return;
    }

    // Get hit information //
    Global3DPoint pdPos = geomDet->surface().toGlobal(isim->localPosition());

    int event = simHit.eventId().event();
    float time_to_detid_ns = pdPos.mag()/(CLHEP::c_light*CLHEP::ns/CLHEP::cm);
    float tof = (*isim).timeOfFlight();
    float toa = tof - time_to_detid_ns;
    float charge = simHit.energyLoss()/GeVperElectron;

    if (verbosity_>1){
        std::cout << " BX # " << bx_true << " Event number " << event << " Raw Id "<< rawid << " Track Id  " << tkid << " Track Pt " << tkpt <<" Time Of Flight " << tof  << " X pos " <<  pdPos.x() << " Y pos " <<  pdPos.y() << " Z pos " << pdPos.z() << " R pos " <<  std::hypot(pdPos.x(),pdPos.y())  << " time_to_detid_ns " << time_to_detid_ns <<" tof " << tof << " toa " << toa << " charge " << charge <<std::endl; 
    }


    // Check if dimensions are fulfilled //
    if (std::hypot(pdPos.x(),pdPos.y()) < dimensions_.first.first || std::hypot(pdPos.x(),pdPos.y()) > dimensions_.first.second){
        if (verbosity_>1){
            std::cout <<"R pos outside ["<<dimensions_.first.first<<","<<dimensions_.first.second<<"]"<<std::endl;
        }
        return;
    }

    if (fabs(pdPos.z()) < dimensions_.second.first || fabs(pdPos.z()) > dimensions_.second.second){
        if (verbosity_>1){
            std::cout <<"Z pos outside ["<<dimensions_.second.first<<","<<dimensions_.second.second<<"]"<<std::endl;
        }
        return;
    }

    // Fill position histograms //
    hits_positions_.positions3D->Fill(pdPos.z(),pdPos.x(),pdPos.y());
    hits_positions_.positions2D->Fill(pdPos.z(),std::hypot(pdPos.x(),pdPos.y())*((pdPos.y()>=0)-(pdPos.y()<0)));
    hits_positions_.positions2DAbs->Fill(fabs(pdPos.z()),std::hypot(pdPos.x(),pdPos.y()));

    // Loop over relative BX //
    int attSampled = 0;
    int attLatched = 0;
    for (int bx = bx_true-bx_range_; bx <= bx_true+bx_range_; bx ++){
        if (verbosity_>2)
            std::cout << "True BX = "<< bx_true << " -> Looking at "<<bx<<std::endl;
        /* Sampled mode */
        if (Phase2TrackerBXHistogram::select_hit(charge,bx,toa,detId,Phase2TrackerBXHistogram::SampledMode)){
            offsetBX_[offset].Sampled->Fill(bx-0.5-1);
            offsetBXMap_.Sampled->Fill(bx-0.5-1,offset);
            if (verbosity_>2)
                std::cout<<"   Sampled fired"<<std::endl;
            attSampled++;
        }
        /* Latched mode */ 
        if (Phase2TrackerBXHistogram::select_hit(charge,bx,toa,detId,Phase2TrackerBXHistogram::LatchedMode)){
            offsetBX_[offset].Latched->Fill(bx-0.5-1);
            offsetBXMap_.Latched->Fill(bx-0.5-1,offset);
            if (verbosity_>2)
                std::cout<<"   Latched fired"<<std::endl;
            attLatched++;
        }
        hitsTrueMap_.Sampled->Fill(bx-0.5-1,offset);
        hitsTrueMap_.Latched->Fill(bx-0.5-1,offset);
    }
    attBXMap_.Sampled->Fill(attSampled,offset);
    attBXMap_.Latched->Fill(attLatched,offset);
}


//
// -- Book Histograms
//
void Phase2TrackerBXHistogram::bookHistograms(DQMStore::IBooker & ibooker,edm::Run const &  iRun ,edm::EventSetup const &  iSetup ) {
    /*
        Book DQM histogram logics 
            - Initialise 2D histograms 
            - Run 1D scan bookings
    */

    ibooker.cd();

    std::string top_folder = config_.getParameter<std::string>("TopFolderName");
    std::stringstream folder_name;
    folder_name << top_folder << "/" << "Hist2D";
    ibooker.setCurrentFolder(folder_name.str());

    std::stringstream HistoName;


    /* Offset scan */
    HistoName.str("");
    HistoName << "OffsetScanSampled";
    offsetBXMap_.Sampled = ibooker.book2D(HistoName.str(), HistoName.str(),
                                          (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5,
                                          offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));
    HistoName.str("");
    HistoName << "OffsetScanLatched";
    offsetBXMap_.Latched = ibooker.book2D(HistoName.str(), HistoName.str(),
                                          (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5,
                                          offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));

    /* Attribution scan */
    HistoName.str("");
    HistoName << "AttributionScanSampled";
    attBXMap_.Sampled = ibooker.book2D(HistoName.str(), HistoName.str(),
                                       5,-0.5,4.5,
                                       offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));
    HistoName.str("");
    HistoName << "AttributionScanLatched";
    attBXMap_.Latched = ibooker.book2D(HistoName.str(), HistoName.str(),
                                       5,-0.5,4.5,
                                       offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));

    /* Efficiency true scan */
    HistoName.str("");
    HistoName << "HitsTrueNumberScanSampled";
    hitsTrueMap_.Sampled = ibooker.book2D(HistoName.str(), HistoName.str(),
                                          (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5,
                                          offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));

    HistoName.str("");
    HistoName << "HitsTrueNumberScanLatched";
    hitsTrueMap_.Latched = ibooker.book2D(HistoName.str(), HistoName.str(),
                                          (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5,
                                          offset_scan_.size(),offset_min_-(offset_step_/2),offset_max_+(offset_step_/2));

    /* Hit positions */
    HistoName.str("");
    HistoName << "HitsPositions3D";
    hits_positions_.positions3D = ibooker.book3D(HistoName.str(), HistoName.str(),
                                                 200,-280.,280.,
                                                 200,-120.,120.,
                                                 200,-120.,120.);
    HistoName.str("");
    HistoName << "HitsPositions2D";
    hits_positions_.positions2D = ibooker.book2D(HistoName.str(), HistoName.str(),
                                                 500,-280.,280.,
                                                 500,-120.,120.);
    HistoName.str("");
    HistoName << "HitsPositions2DAbs";
    hits_positions_.positions2DAbs = ibooker.book2D(HistoName.str(), HistoName.str(),
                                                    1000,0.,280.,
                                                    1000,0.,120.);

    
    /* 1D scans */
    for(std::vector<double>::iterator offset = offset_scan_.begin(); offset != offset_scan_.end(); ++offset) {
        HistModes hist_modes = Phase2TrackerBXHistogram::bookBXHistos(ibooker,*offset);
        offsetBX_.insert(std::make_pair(*offset,hist_modes));
    }
}

Phase2TrackerBXHistogram::HistModes Phase2TrackerBXHistogram::bookBXHistos(DQMStore::IBooker & ibooker,double offset){
    /*
        Book BX histograms 
            - Loop to save BX histogram for specific offset/delay
    */
    std::string top_folder = config_.getParameter<std::string>("TopFolderName");
    std::stringstream folder_name;

    ibooker.cd();
    folder_name << top_folder << "/" << "Hist1D";
    ibooker.setCurrentFolder(folder_name.str());
    if (verbosity_>0){
        std::cout<< "Booking Histograms in : " << folder_name.str()<<"  (offset = "<<offset<<")"<<std::endl;
    }

    std::stringstream HistoName;

    HistModes hist_modes;

    HistoName.str("");
    std::string offsetStr = std::to_string(offset);
    std::replace(offsetStr.begin(), offsetStr.end(), '.', 'p');
    HistoName << "BXHistogramSampledOffset" << offsetStr; 
    hist_modes.Sampled = ibooker.book1D(HistoName.str(), HistoName.str(),
                                        (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5);

    HistoName.str("");
    HistoName << "BXHistogramLatchedOffset"  << offsetStr;
    hist_modes.Latched = ibooker.book1D(HistoName.str(), HistoName.str(),
                                        (2*bx_range_)+1,-static_cast<float>(bx_range_)-0.5,static_cast<float>(bx_range_)+0.5);

    return hist_modes;
}



float Phase2TrackerBXHistogram::getSimTrackPt(EncodedEventId event_id, unsigned int tk_id) {
    /*
        From event and track id, find the pT
    */
    // Make map key
    std::pair<EncodedEventId,unsigned int> key = std::make_pair(event_id,tk_id);
    // If key not in map -> get the track pt 
    if (tracks_pt_.find(key) == tracks_pt_.end()){
        // Set default 
        float pt = 0.;
        // Look into sim track handle
        if (simTrackHandle_.isValid() && pt == 0.){
            for (edm::SimTrackContainer::const_iterator simTrkItr = simTrackHandle_->begin(); simTrkItr != simTrackHandle_->end();    ++simTrkItr) {
                if (simTrkItr->eventId() != event_id)
                    continue;
                if (simTrkItr->trackId() == tk_id){
                    pt = simTrkItr->momentum().Pt();
                    break;
                }
            }
        }

        // Look into particle handle
        if (tParticleHandle_.isValid() && pt == 0.){
            std::vector<TrackingParticle>::const_iterator iterTPart;
            for (iterTPart = tParticleHandle_->begin(); iterTPart != tParticleHandle_->end(); ++iterTPart) {
                /// Make the pointer to the TrackingParticle
                if (iterTPart->eventId() != event_id) 
                    continue;

                /// Loop over SimTracks inside TrackingParticle
                std::vector<SimTrack>::const_iterator iterSimTrack;
                for (iterSimTrack = iterTPart->g4Tracks().begin(); iterSimTrack != iterTPart->g4Tracks().end(); ++iterSimTrack) {
                    if (iterSimTrack->trackId() == tk_id){
                        pt = iterSimTrack->momentum().Pt();
                        break;
                    }
                }
                if (pt > 0.)
                    break;
            }
        }
        // Record it 
        tracks_pt_[key] = pt;
    } 
    // Return saved value
    return tracks_pt_[key];
}


// isPixel 
bool Phase2TrackerBXHistogram::isPixel(const DetId& detId) {
    /*
        Check if hit on detid is pixel
    */
    return (detId.subdetId() == PixelSubdetector::PixelBarrel ||  detId.subdetId() == PixelSubdetector::PixelEndcap);
}

bool Phase2TrackerBXHistogram::isStrip(const DetId& detId) {
    /*
        Check if hit on detid is strip
    */
    return (detId.subdetId() == SiStripDetId::SubDetector::TIB || detId.subdetId() == SiStripDetId::SubDetector::TID || detId.subdetId() == SiStripDetId::SubDetector::TOB || detId.subdetId() == SiStripDetId::SubDetector::TEC);
}


bool Phase2TrackerBXHistogram::select_hit(float charge, int bx, float toa, DetId det_id, int hitDetectionMode){
    /*
        Main select hit logic 
            - Depending on barrel or endcap, use the correct smearing
            - Call correct model
    */
    if (verbosity_>3)
        std::cout<<"Requesting mode "<<hitDetectionMode<<std::endl;
    bool result = false;

    float theThresholdInE = (det_id.subdetId() == StripSubdetector::TOB) ? theThresholdInE_Barrel_ : theThresholdInE_Endcap_;
    float threshold_smearing = 0.;
    if (det_id.subdetId() == StripSubdetector::TOB && theThresholdSmearing_Barrel_>0.){
        threshold_smearing = smearBarrelThresholdDetId(det_id);
    }
    if (det_id.subdetId() != StripSubdetector::TOB && theThresholdSmearing_Endcap_>0.){
        threshold_smearing = smearEndcapThresholdDetId(det_id);
    }
    if (verbosity_>3)
        std::cout<<"Detid : "<<det_id.rawId()<<" -> Threshold = "<<theThresholdInE<<" + "<<threshold_smearing<<std::endl;
    theThresholdInE += threshold_smearing;

    float tofsmeared = 0.;
    if (tof_smearing_ > 0.){
        tofsmeared = smearToFDetId(det_id);                
    }
    if (verbosity_>3)
        std::cout<<"Detid : "<<det_id.rawId()<<" -> TOA = "<<toa<<" + "<<tofsmeared<<std::endl;
    toa += tofsmeared;
    

    if (hitDetectionMode == Phase2TrackerBXHistogram::SampledMode){
        if (verbosity_>3)
            std::cout<<" -> Sampled mode"<<std::endl;
        result = select_hit_sampledMode(charge,bx,toa,det_id,theThresholdInE);
    }
    else if (hitDetectionMode == Phase2TrackerBXHistogram::LatchedMode){
        if (verbosity_>3)
            std::cout<<" -> Latched mode"<<std::endl;
        result = select_hit_latchedMode(charge,bx,toa,det_id,theThresholdInE);
    }
    else {
        result = (toa > theTofLowerCut_ && toa < theTofUpperCut_);
    }
    return result;
}
//
// -- Select Hits in Sampled Mode
//
bool Phase2TrackerBXHistogram::select_hit_sampledMode(float charge, int bx, float toa, DetId det_id, float threshold) const {
    /*
        Hit detect logic : sampled mode
    */
    toa -= bx*bx_time;
    double sampling_time = bx_time;
    double sigScale = getSignalScale(sampling_time - toa);

    if (verbosity_>3){
        std::cout<<"\t(ToF) "<<toa+bx*bx_time<<" -> (corrected for BX "<<bx<<") "<<toa<<std::endl;
        std::cout<<"\tAt time "<<sampling_time-toa<<" :  (scale) "<<sigScale<<" * (charge) "<<charge<< " = "<<sigScale*charge<<" -> Trigger "<<int(sigScale * charge > threshold)<<std::endl;
        if (sigScale * charge > threshold)  std::cout<<"\tPASSED"<<std::endl;
    }

    return (sigScale * charge > threshold);
}
//
// -- Select Hits in Hit Detection Mode
//
bool Phase2TrackerBXHistogram::select_hit_latchedMode(float charge, int bx, float toa, DetId det_id, float threshold) const {
    /*
        Hit detect logic : latched mode
    */
    toa -= bx * bx_time;

    float sampling_time = 0;
    bool lastPulse = true;
    bool aboveThr = false;
    for (float i = deadTime_; i <= bx_time; i++) {
        double sigScale = getSignalScale(sampling_time - toa + i);
        if (verbosity_>3)
            std::cout<<"\tTime "<<sampling_time - toa + i <<" : (scale) "<<sigScale<<" * (charge) "<<charge<< " = "<<sigScale*charge<<" -> Trigger "<<int(sigScale * charge > threshold)<<std::endl;

        aboveThr = (sigScale * charge > threshold);
        if (!lastPulse && aboveThr){
            if (verbosity_>3) std::cout<<"\tPASSED"<<std::endl;
            return true;
        }

        lastPulse = aboveThr;
    }
    return false;
}
double Phase2TrackerBXHistogram::cbc3PulsePolarExpansion(double x) const {
    /*
        Get polar expansion of shape pulse form
        https://indico.cern.ch/event/809430/contributions/3394346/attachments/1829394/2995389/SignalShapeStudy_12042019.pdf
        https://indico.cern.ch/event/777362/contributions/3282560/attachments/1781508/2898378/DigiStudy_Jan18_2019.pdf
        https://indico.cern.ch/event/809436/contributions/3492065/attachments/1875715/3088439/SignalShapeStudy_05072019.pdf
    */
    constexpr size_t max_par = 6;
    if (pulseShapeParameters_.size() < max_par)
        return -1;
    double xOffset = pulseShapeParameters_[0];
    double tau = pulseShapeParameters_[1];
    double r = pulseShapeParameters_[2];
    double theta = pulseShapeParameters_[3];
    int nTerms = static_cast<int>(pulseShapeParameters_[4]);

    double fN = 0;
    double xx = x - xOffset;
    if (xx < 0)
        return 0;

    for (int i = 0; i < nTerms; i++) {
        double angularTerm = 0;
        double temporalTerm = 0;
        double rTerm = std::pow(r, i) / (std::pow(tau, 2. * i) * scaling::nFactorial(i + 2));
        for (int j = 0; j <= i; j++) {
            angularTerm += std::pow(std::cos(theta), (double)(i - j)) * std::pow(std::sin(theta), (double)j);
            temporalTerm += scaling::aScalingConstant(i, j) * std::pow(xx, (double)(i - j)) * std::pow(tau, (double)j);
        }
        double fi = rTerm * angularTerm * temporalTerm;

        fN += fi;
    }
    return fN;
}
double Phase2TrackerBXHistogram::signalShape(double x) const {
    /*
        For specific value of time (x) and the shape parameters, get the value of the signal response
    */
    double xOffset = pulseShapeParameters_[0];
    double tau = pulseShapeParameters_[1];
    double maxCharge = pulseShapeParameters_[5];

    double xx = x - xOffset;
    return maxCharge * (std::exp(-xx / tau) * std::pow(xx / tau, 2.) * cbc3PulsePolarExpansion(x));
}
void Phase2TrackerBXHistogram::storeSignalShape() {
    /*
        Store in vector the shape response 
        -> faster than recalculating at each hit
    */
    pulseShapeVec_.clear();
    for (size_t i = 0; i < interpolationPoints; i++) {
        float val = i / interpolationStep;

        pulseShapeVec_.push_back(signalShape(val));
    }
}
double Phase2TrackerBXHistogram::getSignalScale(double xval) const {
    /*
        Get value of response at specific time
            -> scan the vector to find the value 
    */

    double res = 0.0;
    int len = pulseShapeVec_.size();

    if (xval < 0.0 || xval * interpolationStep >= len)
        return res;

    unsigned int lower = std::floor(xval) * interpolationStep;
    unsigned int upper = std::ceil(xval) * interpolationStep;
    for (size_t i = lower + 1; i < upper * interpolationStep; i++) {
        float val = i * 0.1;
        if (val > xval) {
            res = pulseShapeVec_[i - 1];
            break;
        }
    }
    return res;
}

float Phase2TrackerBXHistogram::smearEndcapThresholdDetId(DetId det_id){
    /*
        Threshold smearing in endcaps
        -> Emulate baseline fluctuations
    */
    std::map<DetId,float>::iterator smear = smearedThresholdFactors_Endcap_.find(det_id);
    if (smear == smearedThresholdFactors_Endcap_.end()){
        float new_smear = smearedThreshold_Endcap_->fire(); 
        smearedThresholdFactors_Endcap_.insert({det_id,new_smear});
        if (verbosity_ > 3){
            std::cout << "New detid " << det_id.rawId() << " given endcap threshold smearing value of " << new_smear << std::endl;
        }
        return new_smear;
    } else{
        if (verbosity_ > 3){
            std::cout << "Known detid " << det_id.rawId() << " with endcap threshold smearing value of " << smear->second << std::endl;
        }
        return smear->second;
    } 
}
float Phase2TrackerBXHistogram::smearBarrelThresholdDetId(DetId det_id){
    /*
        Threshold smearing in barrel
        -> Emulate baseline fluctuations
    */
    std::map<DetId,float>::iterator smear = smearedThresholdFactors_Barrel_.find(det_id);
    if (smear == smearedThresholdFactors_Barrel_.end()){
        float new_smear = smearedThreshold_Barrel_->fire(); 
        smearedThresholdFactors_Barrel_.insert({det_id,new_smear});
        if (verbosity_ > 3){
            std::cout << "New detid " << det_id.rawId() << " given barrel threshold smearing value of " << new_smear << std::endl;
        }
        return new_smear;
    } else{
        if (verbosity_ > 3){
            std::cout << "Known detid " << det_id.rawId() << " with barrel threshold smearing value of " << smear->second << std::endl;
        }
        return smear->second;
    } 
}

float Phase2TrackerBXHistogram::smearToFDetId(DetId det_id){
    /*
        ToF smearing in barrel
        -> Emulate timing uncertainties
    */
    std::map<DetId,float>::iterator smear = smearedTofFactors_.find(det_id);
    if (smear == smearedTofFactors_.end()){
        float new_smear = smearedTOF_->fire(); 
        smearedTofFactors_.insert({det_id,new_smear});
        if (verbosity_ > 3){
            std::cout << "New detid " << det_id.rawId() << " given tof smearing value of " << new_smear << std::endl;
        }
        return new_smear;
    } else{
        if (verbosity_ > 3){
            std::cout << "Known detid " << det_id.rawId() << " with tof smearing value of " << smear->second << std::endl;
        }
        return smear->second;
    } 
}



//define this as a plug-in
DEFINE_FWK_MODULE(Phase2TrackerBXHistogram);
