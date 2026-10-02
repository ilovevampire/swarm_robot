#!/usr/bin/env python3
"""
led_state_controller.py
========================
Drives the AMR's status-LED colour from a simple state topic.

    ROS2 topic `led_state` (std_msgs/String):
        idle | navigating | charging | error
            |
            v
    this node  --(runs the `gz service` CLI)-->  Gazebo service
            |                                    /world/<world>/light_config
            v                                    (built into gz-sim; needs the
    the <light name="led_light"> declared        UserCommands plugin, which our
    in amr_gazebo.xacro changes colour           warehouse.sdf already loads)

CONFIRMED (via `gz service -s /world/warehouse/scene/info ...` - the live
scene graph, not a guess): the light is registered in the running scene
under the PLAIN name declared in the SDF, "led_light" - no model/link
scoping prefix. An earlier version of this file incorrectly used a scoped
default based on an unverified guess; that was wrong and has been reverted.

WHY THIS DESIGN
  * No custom C++ Gazebo plugin needed - light_config already exists.
  * The subscription only records the DESIRED state. A timer applies it.
    So rapid state changes collapse into "latest wins", and if Gazebo isn't
    up yet the node keeps retrying instead of giving up.
  * The topic name is RELATIVE (`led_state`). Run it plain and it is
    /led_state; later, inside a robot namespace, it becomes
    /robot1/led_state automatically - no code change for the fleet.

IMPORTANT LIMITS (read these before debugging)
  * A "true" reply from light_config means the request was ACCEPTED, not that
    it was applied - this is exactly what bit us once already: a wrong light
    name still gets "true" back, and the ONLY evidence of failure is a
    `[Err] [UserCommands.cc] Failed to find light with name [...]` line
    printed in the terminal running Gazebo, which this node cannot see.
    Always check that terminal, not just this node's log, when debugging.
  * light_config re-applies the whole light, so every request re-sends ALL
    the light's properties (LIGHT_PROPS below). Keep them in sync with the
    <light> in amr_gazebo.xacro, or the light's range/attenuation will change
    the first time the colour does.
  * Only the light's colour changes with state. The strip's box has a static
    emissive material (a Gazebo material cannot be recoloured through a
    built-in service).

USAGE
    ros2 run amr_description led_state_controller.py
    ros2 topic pub --once /led_state std_msgs/msg/String "{data: 'charging'}"

PARAMETERS
    world_name (default "warehouse")  - must match <world name="..."> in the SDF
    light_name (default "led_light")  - confirmed via scene/info, see above.
                                        If you ever rename the robot model or
                                        restructure the xacro, re-verify with
                                        scene/info rather than guessing again.
"""

import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# state name -> (r, g, b) diffuse colour, each 0.0-1.0
STATE_COLORS = {
    "idle":       (0.6, 0.6, 0.6),   # dim white
    "navigating": (0.0, 0.3, 1.0),   # blue
    "charging":   (0.0, 1.0, 0.0),   # green
    "error":      (1.0, 0.0, 0.0),   # red
}

# Everything about the light EXCEPT its name and diffuse colour. These values
# mirror the <light> block in amr_gazebo.xacro. Protobuf text format: fields
# are separated by spaces.
LIGHT_PROPS = (
    "type: POINT "
    "specular: {r: 0.3 g: 0.3 b: 0.3 a: 1.0} "
    "attenuation_constant: 0.2 "
    "attenuation_linear: 0.5 "
    "attenuation_quadratic: 0.01 "
    "range: 1.5 "
    "cast_shadows: false "
    "intensity: 1.0 "
)

TICK_PERIOD_S = 0.5      # how often we check "desired vs applied"
RETRY_COOLDOWN_TICKS = 4 # after a failed call, wait 4 ticks (~2 s) before retrying


class LedStateController(Node):

    def __init__(self):
        super().__init__("led_state_controller")

        self.declare_parameter("world_name", "warehouse")
        self.declare_parameter("light_name", "led_light")
        self.world_name = self.get_parameter("world_name").value
        self.light_name = self.get_parameter("light_name").value

        self._desired = "idle"     # what we WANT the LED to show
        self._applied = None       # what Gazebo last ACCEPTED (None = nothing yet)
        self._cooldown = 0         # ticks left before we may retry after a failure

        self.create_subscription(String, "led_state", self._on_state, 10)
        self.create_timer(TICK_PERIOD_S, self._tick)

        self.get_logger().info(
            f"LED controller ready - world '{self.world_name}', "
            f"light '{self.light_name}', listening on 'led_state'"
        )

    # -- input: just remember the latest valid state --------------------
    def _on_state(self, msg: String):
        state = msg.data.strip().lower()
        if state not in STATE_COLORS:
            self.get_logger().warning(
                f"Unknown state '{state}', expected one of {list(STATE_COLORS)}"
            )
            return
        self._desired = state

    # -- output: apply it when it differs from what Gazebo has ----------
    def _tick(self):
        if self._desired == self._applied:
            return
        if self._cooldown > 0:
            self._cooldown -= 1
            return

        if self._send_to_gazebo(self._desired):
            self._applied = self._desired
        else:
            self._cooldown = RETRY_COOLDOWN_TICKS

    def _send_to_gazebo(self, state: str) -> bool:
        r, g, b = STATE_COLORS[state]
        service = f"/world/{self.world_name}/light_config"
        request = (
            f'name: "{self.light_name}" '
            + LIGHT_PROPS
            + f"diffuse: {{r: {r} g: {g} b: {b} a: 1.0}}"
        )
        cmd = [
            "gz", "service",
            "-s", service,
            "--reqtype", "gz.msgs.Light",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "2000",
            "--req", request,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=4.0
            )
        except subprocess.TimeoutExpired:
            self.get_logger().warning(
                "light_config call timed out - is Gazebo running the warehouse "
                "world (it loads the UserCommands plugin)?",
                throttle_duration_sec=5.0,
            )
            return False
        except FileNotFoundError:
            self.get_logger().error(
                "`gz` CLI not found - is Gazebo Harmonic on your PATH?",
                throttle_duration_sec=5.0,
            )
            return False

        if result.returncode != 0 or "true" not in result.stdout.lower():
            self.get_logger().warning(
                f"light_config not accepted (rc={result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}",
                throttle_duration_sec=5.0,
            )
            return False

        self.get_logger().info(
            f"LED -> {state} (r={r} g={g} b={b}); request accepted by Gazebo "
            f"(check the Gazebo terminal too - 'accepted' does not guarantee "
            f"the light was actually found)"
        )
        return True


def main():
    rclpy.init()
    node = LedStateController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
PY_EOF