import { HeroSection } from "./_components/home/hero-section";
import { JourneySection } from "./_components/home/journey-section";
import { SupplierRiskExampleSection } from "./_components/home/supplier-risk-example";
import { CapabilitiesSection } from "./_components/home/capabilities-section";
import { ExplainabilitySection } from "./_components/home/explainability-section";
import { CtaSection } from "./_components/home/cta-section";

export default function Home() {
  return (
    <div className="max-w-3xl">
      <HeroSection />
      <JourneySection />
      <SupplierRiskExampleSection />
      <CapabilitiesSection />
      <ExplainabilitySection />
      <CtaSection />
    </div>
  );
}
