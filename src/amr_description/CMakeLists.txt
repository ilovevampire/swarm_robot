cmake_minimum_required(VERSION 3.8)
project(amr_description)

find_package(ament_cmake REQUIRED)

# ---------------------------------------------------------------------------
# Install every folder the package needs at runtime (URDF, worlds, launch
# files, rviz config, controller config) into share/amr_description/.
# Anything not listed below simply won't exist at runtime, even if it
# exists in your src/ folder.
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
# Install Python executables as runnable nodes. lib/${PROJECT_NAME}/ is
# where `ros2 run amr_description <name>` looks - NOT share/.
# ---------------------------------------------------------------------------
install(PROGRAMS
  scripts/led_state_controller.py
  scripts/twist_to_stamped.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
