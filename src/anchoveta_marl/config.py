from dataclasses import dataclass


PORTS = {
    "Malabrigo": (-79.44141666666667, -7.692789583333334),
    "Chimbote": (-78.9475, -9.075833333333334),
    "Callao": (-77.14027777777778, -12.045),
}


@dataclass(frozen=True)
class FleetConfig:
    n_agents: int = 15
    boats_per_port: int = 5
    capacity_t: float = 500.0
    speed_out_kn: float = 12.5
    speed_return_kn: float = 11.5
    reference_fuel_lph: float = 209.5
    max_boats_per_zone: int = 3

    @property
    def fuel_l_per_nm_out(self) -> float:
        return self.reference_fuel_lph / self.speed_out_kn

    @property
    def fuel_l_per_nm_return(self) -> float:
        return self.reference_fuel_lph / self.speed_return_kn
