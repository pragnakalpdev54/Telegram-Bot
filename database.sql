DROP TABLE IF EXISTS `user_details`;


CREATE TABLE `user_details` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `chat_id` int(11) NOT NULL,
  `user_first_name` varchar(60) DEFAULT NULL,
  `user_create_date` timestamp NOT NULL DEFAULT current_timestamp,
  `user_entry_date` timestamp NOT NULL DEFAULT current_timestamp,
  `user_login_date` timestamp NULL DEFAULT '2024-01-01 18:29:59',
  `user_api_token` varchar(60) DEFAULT NULL,
  `no_of_questions` int,
  `no_of_documents` int,
  `is_user` tinyint(1) DEFAULT 0,
  `is_limit_reached` tinyint(1) DEFAULT 0,

  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;


