SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

CREATE TABLE `kicked_users` (
  `id` int(11) NOT NULL,
  `user_id` bigint(11) NOT NULL,
  `chat_id` bigint(11) NOT NULL,
  `time` date NOT NULL,
  `message` varchar(2048) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `suspicious_messages` (
  `id` int(11) NOT NULL,
  `user_id` bigint(11) NOT NULL,
  `group_id` bigint(11) NOT NULL,
  `date` datetime DEFAULT CURRENT_TIMESTAMP,
  `message` varchar(2048) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `suspicious_users` (
  `id` int(11) NOT NULL,
  `user_id` bigint(11) NOT NULL,
  `date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `group_id` bigint(13) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


ALTER TABLE `kicked_users`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `suspicious_messages`
  ADD PRIMARY KEY (`id`);

ALTER TABLE `suspicious_users`
  ADD PRIMARY KEY (`id`);


ALTER TABLE `kicked_users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `suspicious_messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
ALTER TABLE `suspicious_users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
