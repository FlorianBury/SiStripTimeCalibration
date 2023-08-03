#ifndef Phase2TrackerBXHistogram_h
#define Phase2TrackerBXHistogram_h

#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/ESHandle.h"

#include "DataFormats/Common/interface/Handle.h"
#include "DataFormats/SiStripDetId/interface/SiStripDetId.h"
#include "DataFormats/DetId/interface/DetId.h"

#include "Geometry/Records/interface/TrackerTopologyRcd.h"
#include "Geometry/Records/interface/TrackerDigiGeometryRecord.h"

#include "SimDataFormats/CrossingFrame/interface/CrossingFrame.h"
#include "SimDataFormats/TrackingAnalysis/interface/TrackingParticle.h"

#include "DQMServices/Core/interface/DQMEDAnalyzer.h"

#include "CLHEP/Units/GlobalPhysicalConstants.h"
#include "CLHEP/Units/GlobalSystemOfUnits.h"

// DQM Histograming
class MonitorElement;
class PixelDigiSimLink;
class SimTrack;
class TrackingParticle;
class SimHit;
class TrackerTopology;
class PixelDigi;
class Phase2TrackerDigi;
class TrackerGeometry;
class TF1;
class TTree;

namespace CLHEP {
  class HepRandomEngine;
  class RandGaussQ;
  class RandFlat;
}  // namespace CLHEP


class Phase2TrackerBXHistogram : public DQMEDAnalyzer{

    public:

        // Constructor //
        explicit Phase2TrackerBXHistogram(const edm::ParameterSet&);
        // Destructor //
        ~Phase2TrackerBXHistogram() override;
        // Initialize run parameters //
        void dqmBeginRun(const edm::Run& iRun, const edm::EventSetup& iSetup) override;
        // Analyse : loop over delays and use runSimHit for each //
        void analyze(const edm::Event& iEvent, const edm::EventSetup& iSetup) override;
        // Logic to run over hits and check triggering //
        template <typename T>
        void runSimHit(T isim,double offset, const TrackerTopology* tTopo,const TrackerGeometry* tGeom);

        // Logics to check whether pixel or strip hit and get track pT //
        bool isPixel(const DetId& detId);
        bool isStrip(const DetId& detId);
        float getSimTrackPt(EncodedEventId event_id, unsigned int tk_id);

        // Structures //
        struct HistModes{ // Base histogram containers
            MonitorElement* Sampled;
            MonitorElement* Latched;
        };

        struct HitsPositions{  // Save hit positions
            MonitorElement* positions3D;
            MonitorElement* positions2D;
            MonitorElement* positions2DAbs;
        };
        // Histogram booking //
        void bookHistograms(DQMStore::IBooker & ibooker, edm::Run const &  iRun ,
                edm::EventSetup const &  iSetup ) override;
        HistModes bookBXHistos(DQMStore::IBooker & ibooker,double offset); // Book BX for each delay in loop


        // Separators for each set of modules //
        std::map<std::string,std::pair<std::pair<float,float>,std::pair<float,float>>> dims_per_subdet =
        {   // name {r_min,r_max}, {z_min,z_max}
            {"ALL", {{0.,120.} , {0.,280.}}},
            {"BLL", {{20.,26.} , {0.,6.5}}},
            {"BLH", {{22.,30.} , {116.,122.}}},
            {"BHL", {{108.,114.} , {0.,20.}}},
            {"BHH", {{108.,114.} , {80.,120.}}},
            {"ELL", {{22.,28.} , {128.,131.}}},
            {"ELH", {{32.,50.5} , {260.,270.}}},
            {"EHL", {{93.,112.} , {128.,131.}}},
            {"EHH", {{92.,112.} , {262.,268.}}},
        };


    private:


        // EDM variables //
        edm::ParameterSet config_;

        std::string geomType_;
        edm::InputTag simTrackSrc_;
        edm::InputTag simVertexSrc_;
        std::vector<edm::InputTag> pSimHitSrc_;
        std::vector<edm::InputTag> pMixSimHitSrc_;
        const edm::InputTag puSummarySrc_;
        edm::InputTag tParticleSrc_;


        const edm::EDGetTokenT<std::vector<TrackingParticle> > tParticleToken_;
        edm::Handle<std::vector<TrackingParticle> > tParticleHandle_;
        std::vector< std::pair<edm::InputTag,edm::EDGetTokenT< edm::PSimHitContainer >> > simHitTokens_;
        std::vector< std::pair<edm::InputTag,edm::EDGetTokenT< CrossingFrame<PSimHit> >> > mixSimHitTokens_;
        const edm::EDGetTokenT<edm::SimTrackContainer> simTrackToken_;

        edm::Handle<edm::SimTrackContainer> simTrackHandle_;

        const edm::ESGetToken<TrackerTopology, TrackerTopologyRcd> topoToken_;
        const edm::ESGetToken<TrackerGeometry, TrackerDigiGeometryRecord> geomToken_;


        // Histograms related variables //
        std::map<double, HistModes> offsetBX_;
        HistModes offsetBXMap_;
        HistModes attBXMap_;
        HistModes hitsTrueMap_;
    
        HitsPositions hits_positions_;

        // Signal shape //
        std::vector<double> pulseShapeVec_;
        double cbc3PulsePolarExpansion(double x) const;
        double signalShape(double x) const;
        double getSignalScale(double xval) const;
        void storeSignalShape();

        // Select hit variables //
        static constexpr float bx_time{25};
        static constexpr size_t interpolationPoints{1000};
        static constexpr int interpolationStep{10};

        // Select Hit logics //
        enum { SquareWindow, SampledMode, LatchedMode, SampledOrLatchedMode, HIPFindingMode };
        bool select_hit(float charge, int bx, float toa, DetId det_id, int hitDetectionMode);
        bool select_hit_sampledMode(float charge, int bx, float toa, DetId det_id, float threshold) const;
        bool select_hit_latchedMode(float charge, int bx, float toa, DetId det_id, float threshold) const;

        // Config parameters //
        std::vector<double> pulseShapeParameters_;
        bool use_mixing_;
        std::string mode_;
        std::string subdet_;
        bool fireRandom_;
        int bx_range_;
        float deadTime_;
        double pTCut_;
        double theTofLowerCut_;
        double theTofUpperCut_;
        double offset_min_;
        double offset_max_;
        double offset_step_;
        double offset_emulate_;
        std::vector<double> offset_scan_;
        double theThresholdInE_Endcap_;
        double theThresholdInE_Barrel_;
        double theThresholdSmearing_Endcap_;
        double theThresholdSmearing_Barrel_;
        double tof_smearing_;

        const float GeVperElectron; // 3.7E-09 
        int verbosity_;


        // Containers // 
        std::pair<std::pair<float,float>,std::pair<float,float>> dimensions_; // Dimensions to select modules 
        std::map<std::pair<EncodedEventId,unsigned int>,float> tracks_pt_;    // cache for tracke pTs
        
        // Threshold gaussian smearing:
    //
        float smearEndcapThresholdDetId(DetId);
        float smearBarrelThresholdDetId(DetId);
        float smearToFDetId(DetId);

        std::unique_ptr<CLHEP::RandFlat> smearedThreshold_Endcap_;                          
        std::unique_ptr<CLHEP::RandFlat> smearedThreshold_Barrel_;
        std::unique_ptr<CLHEP::RandFlat> smearedTOF_;
        
        // smearing vectors 
        std::map<DetId,float> smearedThresholdFactors_Endcap_;
        std::map<DetId,float> smearedThresholdFactors_Barrel_;
        std::map<DetId,float> smearedTofFactors_;

};
#endif
