import wpilib
import rev
from numpy import interp
from magicbot import feedback


class Shooter:
    outer_motor: rev.CANSparkMax
    centre_motor: rev.CANSparkMax
    loading_piston: wpilib.Solenoid

    ranges = (7, 8, 9, 10, 11)
    centre_rpms = (880, 1120, 1500, 2150, 2400)

    def __init__(self):
        self.outer_rpm = 0
        self.centre_rpm = 0

        self.inject = False
        self.in_range = False
        self.velocity_tolerance = 50  # rpm

    def on_enable(self) -> None:
        self.centre_motor.stopMotor()
        self.outer_motor.stopMotor()

    def setup(self) -> None:
        self.loading_piston.setPulseDuration(0.5)
        self.outer_motor.setIdleMode(rev.CANSparkMax.IdleMode.kCoast)
        self.centre_motor.setIdleMode(rev.CANSparkMax.IdleMode.kCoast)

        self.outer_motor.setInverted(False)
        self.centre_motor.setInverted(True)

        self.outer_encoder = self.outer_motor.getEncoder()
        self.centre_encoder = self.centre_motor.getEncoder()

        self.centre_pid = self.centre_motor.getPIDController()
        self.outer_pid = self.outer_motor.getPIDController()

        self.outer_pid.setP(0.0279 / 60)
        self.outer_pid.setI(1e-6)
        self.outer_pid.setD(0)
        self.outer_pid.setFF(0.000156)
        self.centre_pid.setP(0.0247 / 60)
        self.centre_pid.setI(1e-6)
        self.centre_pid.setD(0)
        self.centre_pid.setFF(0.000156)

    def execute(self) -> None:
        self.centre_pid.setReference(self.centre_rpm, rev.ControlType.kVelocity)
        self.outer_pid.setReference(self.outer_rpm, rev.ControlType.kVelocity)

        if self.inject:
            self.loading_piston.startPulse()
            self.inject = False

    def set_range(self, dist: float) -> None:
        """
        Set the target range for the shooter, this will be converted into target speeds for the flywheels
        dist: planar distance from the power port
        """
        if self.ranges[0] <= dist <= self.ranges[-1]:
            self.in_range = True
        else:
            # clamp the range between our minimum and maximum
            dist = min(self.ranges[-1], max(dist, self.ranges[0]))
            self.in_range = False
        self.centre_rpm = interp(dist, self.ranges, self.centre_rpms)
        self.outer_rpm = 5000

    def is_at_speed(self) -> bool:
        """
        Returns true if the shooter is spinning at the set speed.

        Considers the rotation rates of the flywheels compared with their setpoints
        """
        return (
            abs(self.centre_rpm - self.centre_encoder.getVelocity())
            <= self.velocity_tolerance
            and abs(self.outer_rpm - self.outer_encoder.getVelocity())
            <= self.velocity_tolerance
        )

    @feedback
    def get_centre_velocity(self):
        return self.centre_encoder.getVelocity()

    @feedback
    def get_outer_velocity(self):
        return self.outer_encoder.getVelocity()

    def is_firing(self) -> bool:
        """
        Returns true if the shooter is attempting a shot.

        based off of the pistons current state
        """
        return not self.loading_piston.get()

    def is_in_range(self) -> bool:
        """
        Returns true if the current target of the shooter is within range
        Returns false if the range has been clamped
        """
        return self.in_range

    def is_ready(self) -> bool:
        """
        Returns true if the shooter is ready to take a shot.

        Checks the speed, range and whether the piston is moving
        """
        # print(f"in range {self.is_in_range()} at speed {self.is_at_speed()} is firing {self.is_firing()}")
        return self.is_in_range() and self.is_at_speed() and not self.is_firing()

    def fire(self) -> None:
        """
        Inject a ball into the shooter
        """
        self.inject = True
