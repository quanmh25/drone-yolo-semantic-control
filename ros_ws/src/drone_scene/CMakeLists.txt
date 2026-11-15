cmake_minimum_required(VERSION 3.8)
project(drone_scene)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch worlds models urdf config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
