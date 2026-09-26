cmake_minimum_required(VERSION 3.8)
project(amr_description)

find_package(ament_cmake REQUIRED)

# ---------------------------------------------------------------------------
# Install every folder the package needs at runtime (URDF, worlds, launch
# files, rviz config, controller config) into share/amr_description/.
# This is the ROS2 convention: get_package_share_directory("amr_description")
# in Python, or $(find amr_description) inside xacro, both resolve here.
# Anything not listed below simply won't exist at runtime, even if it
# exists in your src/ folder - a very common "why can't it find my file"
# bug for beginners.
# ---------------------------------------------------------------------------
install(DIRECTORY
  urdf
  worlds
  launch
  rviz
  config
  DESTINATION share/${PROJECT_NAME}
)

# ---------------------------------------------------------------------------
# Install the Python LED controller as a runnable executable.
# lib/${PROJECT_NAME}/ is where `ros2 run amr_description <name>` looks -
# NOT share/. This is a separate ROS2 convention: share/ = data/resources,
# lib/<pkg>/ = executables. Mixing these up is another common beginner trap.
# ---------------------------------------------------------------------------
install(PROGRAMS
  scripts/led_state_controller.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()