from enum import StrEnum

from negotiation.records import RoleName


class Role(StrEnum):
    BUYER = "buyer"
    SELLER = "seller"

    @property
    def opponent(self) -> "Role":
        return Role.SELLER if self is Role.BUYER else Role.BUYER

    @property
    def record_name(self) -> RoleName:
        return "buyer" if self is Role.BUYER else "seller"
