// Gazebo helpers for fourWheelRobot, in one process:
//   - a black trail drawn on the ground behind the robot
//   - a third-person chase camera (press K in the sim window to toggle free camera)
//
// Talks to Gazebo directly over ign-transport. The old Python scripts shelled out
// to the `ign` CLI (a slow-starting Ruby wrapper) for every trail segment, which
// could not keep up with the robot and starved the simulator of CPU.
//
// Usage: sim_helpers <model_name>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <ignition/math/Color.hh>
#include <ignition/math/Pose3.hh>
#include <ignition/math/Vector3.hh>
#include <ignition/msgs.hh>
#include <ignition/transport/Node.hh>

namespace msgs = ignition::msgs;
namespace math = ignition::math;

constexpr double STEP = 0.05;      // metres of travel between trail samples
constexpr double WIDTH = 0.08;     // bar width (m)
constexpr double HEIGHT = 0.01;    // bar thickness (m)
constexpr double STRAIGHT = 0.01;  // max sideways drift (m) before a new bar starts
constexpr int K_KEY = 75;          // Qt::Key_K

class SimHelpers
{
public:
  explicit SimHelpers(std::string model) : model_(std::move(model)) {}

  void Run()
  {
    const std::string topic = FindPoseTopic();
    node_.Subscribe(topic, &SimHelpers::OnPoses, this);
    node_.Subscribe("/keyboard/keypress", &SimHelpers::OnKey, this);

    // The robot is spawned after the GUI starts. Wait for it, then send the
    // follow request once. Re-sending repeatedly would reset the camera and
    // fight the user's zoom.
    std::unique_lock<std::mutex> lock(mtx_);
    cv_.wait(lock, [this] { return robot_seen_; });
    lock.unlock();
    std::this_thread::sleep_for(std::chrono::seconds(1));
    bool following = true;
    SetFollow(following);

    while (true) {
      lock.lock();
      cv_.wait(lock, [this] { return toggles_ > 0; });
      --toggles_;
      lock.unlock();
      following = !following;
      SetFollow(following);
    }
  }

private:
  // Wait for the sim to come up, then find its world's pose topic
  std::string FindPoseTopic()
  {
    while (true) {
      std::vector<std::string> topics;
      node_.TopicList(topics);
      for (const auto & t : topics) {
        const std::string suffix = "/dynamic_pose/info";
        if (t.rfind("/world/", 0) == 0 && t.size() > suffix.size() &&
            t.compare(t.size() - suffix.size(), suffix.size(), suffix) == 0) {
          return t;
        }
      }
      std::this_thread::sleep_for(std::chrono::seconds(1));
    }
  }

  void OnPoses(const msgs::Pose_V & msg)
  {
    for (const auto & p : msg.pose()) {
      if (p.name() != model_) {
        continue;
      }
      if (!robot_seen_) {
        std::lock_guard<std::mutex> lock(mtx_);
        robot_seen_ = true;
        cv_.notify_all();
      }
      AddTrailPoint(p.position().x(), p.position().y());
    }
  }

  // Straight stretches are one bar that keeps getting longer (same marker id);
  // a new bar only starts when the path bends. That keeps the number of visuals
  // Gazebo has to render small even after a long drive.
  void AddTrailPoint(double x, double y)
  {
    if (!have_last_) {
      last_x_ = x;
      last_y_ = y;
      have_last_ = true;
      return;
    }
    if (std::hypot(x - last_x_, y - last_y_) < STEP) {
      return;
    }

    bool extend = false;
    if (run_id_ > 0) {
      // Sideways distance of the new point from the current bar's line
      const double drift = std::abs((x - run_x_) * std::sin(run_yaw_) -
                                    (y - run_y_) * std::cos(run_yaw_));
      const double ahead = (x - run_x_) * std::cos(run_yaw_) +
                           (y - run_y_) * std::sin(run_yaw_);
      extend = drift < STRAIGHT && ahead > 0;
    }
    if (!extend) {
      ++run_id_;
      run_x_ = last_x_;
      run_y_ = last_y_;
      run_yaw_ = std::atan2(y - last_y_, x - last_x_);
    }
    DrawBar(run_id_, run_x_, run_y_, x, y);
    last_x_ = x;
    last_y_ = y;
  }

  void DrawBar(int id, double ax, double ay, double bx, double by)
  {
    const double length = std::hypot(bx - ax, by - ay) + WIDTH;  // overlap so corners join
    const double yaw = std::atan2(by - ay, bx - ax);

    msgs::Marker m;
    m.set_ns("trail");
    m.set_id(id);
    m.set_action(msgs::Marker::ADD_MODIFY);
    m.set_type(msgs::Marker::BOX);
    msgs::Set(m.mutable_scale(), math::Vector3d(length, WIDTH, HEIGHT));
    msgs::Set(m.mutable_pose(),
              math::Pose3d((ax + bx) / 2, (ay + by) / 2, HEIGHT / 2 + 0.002, 0, 0, yaw));
    msgs::Set(m.mutable_material()->mutable_ambient(), math::Color(0, 0, 0, 1));
    msgs::Set(m.mutable_material()->mutable_diffuse(), math::Color(0, 0, 0, 1));
    // /marker is a oneway service: fire and forget, no reply to wait for
    node_.Request("/marker", m);
  }

  void OnKey(const msgs::Int32 & msg)
  {
    if (msg.data() == K_KEY) {
      std::lock_guard<std::mutex> lock(mtx_);
      ++toggles_;
      cv_.notify_all();
    }
  }

  void SetFollow(bool on)
  {
    msgs::Boolean rep;
    bool result;
    if (on) {
      msgs::Vector3d offset;
      offset.set_x(-3);
      offset.set_y(0);
      offset.set_z(1.5);
      node_.Request("/gui/follow/offset", offset, 2000, rep, result);
    }
    msgs::StringMsg req;
    req.set_data(on ? model_ : "");
    node_.Request("/gui/follow", req, 2000, rep, result);
  }

  ignition::transport::Node node_;
  std::string model_;

  // Trail state, only touched from the pose callback
  bool have_last_ = false;
  double last_x_ = 0, last_y_ = 0;
  int run_id_ = 0;
  double run_x_ = 0, run_y_ = 0, run_yaw_ = 0;

  // Shared between the transport callbacks and the main thread
  std::mutex mtx_;
  std::condition_variable cv_;
  bool robot_seen_ = false;
  int toggles_ = 0;
};

int main(int argc, char ** argv)
{
  // When started as a launch_ros Node, extra --ros-args follow the model name
  SimHelpers helpers(argc > 1 ? argv[1] : "demo_bot");
  helpers.Run();
  return 0;
}
