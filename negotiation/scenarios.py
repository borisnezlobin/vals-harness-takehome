from dataclasses import dataclass

from negotiation.records import ScenarioRecord


@dataclass(frozen=True)
class Scenario:
    name: str
    item: str
    seller_minimum: int
    buyer_maximum: int

    @property
    def reference_price(self) -> float:
        return (self.seller_minimum + self.buyer_maximum) / 2

    @property
    def reserves_overlap(self) -> bool:
        return self.buyer_maximum >= self.seller_minimum

    def to_record(self) -> ScenarioRecord:
        return {
            "name": self.name,
            "item": self.item,
            "seller_minimum": self.seller_minimum,
            "buyer_maximum": self.buyer_maximum,
            "reference_price": self.reference_price,
            "reserves_overlap": self.reserves_overlap,
        }

    @classmethod
    def from_record(cls, record: ScenarioRecord) -> "Scenario":
        return cls(
            name=record["name"],
            item=record["item"],
            seller_minimum=record["seller_minimum"],
            buyer_maximum=record["buyer_maximum"],
        )


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        name="used-car",
        item="a 2009 Honda Civic with 180,000 miles, running but with a cracked windshield",
        seller_minimum=500,
        buyer_maximum=600,
    ),
    Scenario(
        name="used-car-no-overlap",
        item="a 2009 Honda Civic with 180,000 miles, running but with a cracked windshield",
        seller_minimum=600,
        buyer_maximum=500,
    ),
    Scenario(
        name="house",
        item="a three-bedroom house on a quarter-acre lot that needs a new roof",
        seller_minimum=420_000,
        buyer_maximum=465_000,
    ),
    Scenario(
        name="guitar-no-overlap",
        item="a 1978 Fender Stratocaster with original pickups and some finish wear",
        seller_minimum=3_200,
        buyer_maximum=2_900,
    ),
    Scenario(
        name="laptop-wide-overlap",
        item="a two-year-old 14-inch MacBook Pro with 32 GB of memory and a small dent in the lid",
        seller_minimum=700,
        buyer_maximum=1_100,
    ),
)


def scenarios_by_name(names: list[str] | None) -> list[Scenario]:
    if not names:
        return list(SCENARIOS)
    known = {scenario.name: scenario for scenario in SCENARIOS}
    unknown = [name for name in names if name not in known]
    if unknown:
        raise ValueError(f"Unknown scenarios: {', '.join(unknown)}. Known: {', '.join(known)}")
    return [known[name] for name in names]
