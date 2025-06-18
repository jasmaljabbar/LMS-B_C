/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.11-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: cloudnative_lms
-- ------------------------------------------------------
-- Server version	10.11.11-MariaDB-0ubuntu0.24.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `assessment_lesson_association`
--

DROP TABLE IF EXISTS `assessment_lesson_association`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessment_lesson_association` (
  `assessment_id` int(11) NOT NULL,
  `lesson_id` int(11) NOT NULL,
  PRIMARY KEY (`assessment_id`,`lesson_id`),
  KEY `lesson_id` (`lesson_id`),
  CONSTRAINT `assessment_lesson_association_ibfk_1` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
  CONSTRAINT `assessment_lesson_association_ibfk_2` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessment_lesson_association`
--

LOCK TABLES `assessment_lesson_association` WRITE;
/*!40000 ALTER TABLE `assessment_lesson_association` DISABLE KEYS */;
INSERT INTO `assessment_lesson_association` VALUES
(1,1);
/*!40000 ALTER TABLE `assessment_lesson_association` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assessments`
--

DROP TABLE IF EXISTS `assessments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assessments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `subject_id` int(11) DEFAULT NULL,
  `creation_date` datetime DEFAULT current_timestamp(),
  `created_by_user_id` int(11) DEFAULT NULL,
  `due_date` datetime DEFAULT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`content`)),
  `assignment_format_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_assessments_id` (`id`),
  KEY `ix_assessments_subject_id` (`subject_id`),
  KEY `ix_assessments_assignment_format_id` (`assignment_format_id`),
  KEY `ix_assessments_created_by_user_id` (`created_by_user_id`),
  CONSTRAINT `assessments_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE SET NULL,
  CONSTRAINT `assessments_ibfk_2` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `assessments_ibfk_3` FOREIGN KEY (`assignment_format_id`) REFERENCES `assignment_formats` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assessments`
--

LOCK TABLES `assessments` WRITE;
/*!40000 ALTER TABLE `assessments` DISABLE KEYS */;
INSERT INTO `assessments` VALUES
(1,'Physics Assignment Term 2025 - 1','Physics Assignment Term 2025 - 1',1,'2025-04-15 17:48:48',2,'2025-04-15 16:38:18','[{\"question_number\": 1, \"question_type\": \"single_select\", \"question_text\": \"Sound is primarily produced by which of the following?\", \"options\": [\"Stationary objects\", \"Vibrating objects\", \"Objects absorbing light\", \"Objects at high temperature\"], \"correct_answer\": \"Vibrating objects\", \"explanation\": \"Sound is defined as a form of energy carried by waves produced by vibrating objects.\", \"reference_page\": 94, \"reference_section\": \"HOW SOUND IS PRODUCED\"}, {\"question_number\": 2, \"question_type\": \"single_select\", \"question_text\": \"What is essential for the propagation of sound waves?\", \"options\": [\"A vacuum\", \"Complete darkness\", \"A medium (solid, liquid, or gas)\", \"High pressure only\"], \"correct_answer\": \"A medium (solid, liquid, or gas)\", \"explanation\": \"Sound requires a material medium (like solid, liquid, or gas) to travel from one place to another; it cannot travel in a vacuum.\", \"reference_page\": 96, \"reference_section\": \"Propagation of Sound\"}, {\"question_number\": 3, \"question_type\": \"single_select\", \"question_text\": \"In general, sound travels fastest through which state of matter?\", \"options\": [\"Solids\", \"Liquids\", \"Gases\", \"Vacuum\"], \"correct_answer\": \"Solids\", \"explanation\": \"Sound travels fastest in solids, slower in liquids, and slowest in gases because the particles are most closely packed in solids, facilitating easier energy transfer.\", \"reference_page\": 98, \"reference_section\": \"Propagation of Sound in Solid, Liquid and Gas\"}, {\"question_number\": 4, \"question_type\": \"single_select\", \"question_text\": \"What term describes the maximum displacement of a particle in a wave from its mean or rest position?\", \"options\": [\"Frequency\", \"Wavelength\", \"Amplitude\", \"Time Period\"], \"correct_answer\": \"Amplitude\", \"explanation\": \"Amplitude is the maximum displacement of a wave from its mean position and is related to the loudness of the sound.\", \"reference_page\": 99, \"reference_section\": \"TERMS RELATED TO A SOUND WAVE\"}, {\"question_number\": 5, \"question_type\": \"single_select\", \"question_text\": \"The number of vibrations or oscillations completed by a vibrating body in one second is known as:\", \"options\": [\"Amplitude\", \"Frequency\", \"Time Period\", \"Wavelength\"], \"correct_answer\": \"Frequency\", \"explanation\": \"Frequency is defined as the number of vibrations produced by a vibrating body in one second.\", \"reference_page\": 99, \"reference_section\": \"TERMS RELATED TO A SOUND WAVE\"}, {\"question_number\": 6, \"question_type\": \"single_select\", \"question_text\": \"What is the standard SI unit used to measure frequency?\", \"options\": [\"Metre (m)\", \"Second (s)\", \"Hertz (Hz)\", \"Decibel (dB)\"], \"correct_answer\": \"Hertz (Hz)\", \"explanation\": \"The SI unit used to measure frequency is Hertz (Hz). 1 Hz means one vibration per second.\", \"reference_page\": 99, \"reference_section\": \"TERMS RELATED TO A SOUND WAVE\"}, {\"question_number\": 7, \"question_type\": \"single_select\", \"question_text\": \"What is the typical range of sound frequencies that are audible to human beings?\", \"options\": [\"Below 20 Hz\", \"20 Hz to 20,000 Hz\", \"Above 20,000 Hz\", \"Only 1000 Hz\"], \"correct_answer\": \"20 Hz to 20,000 Hz\", \"explanation\": \"Human beings can typically hear sounds with frequencies between 20 Hz and 20,000 Hz. Sounds below 20 Hz are infrasonic, and above 20,000 Hz are ultrasonic.\", \"reference_page\": 102, \"reference_section\": \"Audible and Inaudible Sounds\"}, {\"question_number\": 8, \"question_type\": \"single_select\", \"question_text\": \"What is the phenomenon called when a sound wave bounces off a surface and is heard again after the original sound?\", \"options\": [\"Refraction\", \"Diffraction\", \"Echo\", \"Interference\"], \"correct_answer\": \"Echo\", \"explanation\": \"An echo is the reflection of sound that reaches a listener with a delay after the direct sound is heard, typically when sound bounces off a distant surface.\", \"reference_page\": 104, \"reference_section\": \"Echoes\"}, {\"question_number\": 9, \"question_type\": \"single_select\", \"question_text\": \"The technology SONAR (Sound Navigation and Ranging) primarily utilizes which property of sound waves?\", \"options\": [\"Reflection\", \"Refraction\", \"Diffraction\", \"Interference\"], \"correct_answer\": \"Reflection\", \"explanation\": \"SONAR works on the principle of reflection of sound. It sends out ultrasonic waves and detects the reflected waves to locate underwater objects or determine depth.\", \"reference_page\": 104, \"reference_section\": \"SONAR\"}, {\"question_number\": 10, \"question_type\": \"single_select\", \"question_text\": \"When a parallel beam of light falls on a highly polished surface like a mirror, what type of reflection occurs?\", \"options\": [\"Diffused reflection\", \"Irregular reflection\", \"Specular reflection\", \"Scattered reflection\"], \"correct_answer\": \"Specular reflection\", \"explanation\": \"Reflection from a smooth, polished surface where parallel incident rays remain parallel after reflection is called regular or specular reflection.\", \"reference_page\": 52, \"reference_section\": \"Regular reflection\"}, {\"question_number\": 11, \"question_type\": \"single_select\", \"question_text\": \"According to the laws of reflection, how does the angle of incidence (i) relate to the angle of reflection (r)?\", \"options\": [\"Angle i > Angle r\", \"Angle i < Angle r\", \"Angle i = Angle r\", \"Angle i + Angle r = 90\\u00b0\"], \"correct_answer\": \"Angle i = Angle r\", \"explanation\": \"The second law of reflection states that the angle of incidence is always equal to the angle of reflection.\", \"reference_page\": 52, \"reference_section\": \"LAWS OF REFLECTION\"}, {\"question_number\": 12, \"question_type\": \"single_select\", \"question_text\": \"Which of the following best describes the image formed by a standard plane mirror?\", \"options\": [\"Real and inverted\", \"Real and upright\", \"Virtual and inverted\", \"Virtual and upright\"], \"correct_answer\": \"Virtual and upright\", \"explanation\": \"A plane mirror forms an image that is virtual (cannot be projected on a screen) and upright (erect).\", \"reference_page\": 56, \"reference_section\": \"Characteristics of an Image formed by a Plane Mirror\"}, {\"question_number\": 13, \"question_type\": \"single_select\", \"question_text\": \"What is the term for the effect seen in a plane mirror where the left side of an object appears as the right side in the image, and vice versa?\", \"options\": [\"Reflection inversion\", \"Lateral inversion\", \"Spherical aberration\", \"Diffraction\"], \"correct_answer\": \"Lateral inversion\", \"explanation\": \"Lateral inversion is the phenomenon in a mirror where the left side of an object appears to be the right side in its image and vice versa.\", \"reference_page\": 54, \"reference_section\": \"Lateral Inversion\"}, {\"question_number\": 14, \"question_type\": \"single_select\", \"question_text\": \"Which set of colours are considered the primary colours of light for additive colour mixing?\", \"options\": [\"Red, Yellow, Blue\", \"Red, Green, Blue\", \"Cyan, Magenta, Yellow\", \"Orange, Green, Violet\"], \"correct_answer\": \"Red, Green, Blue\", \"explanation\": \"The primary colours of light are Red, Green, and Blue (RGB). When combined in the correct intensities, they produce white light.\", \"reference_page\": 57, \"reference_section\": \"PRIMARY COLOURS\"}, {\"question_number\": 15, \"question_type\": \"single_select\", \"question_text\": \"What secondary colour is produced when beams of red light and green light overlap?\", \"options\": [\"Cyan\", \"Magenta\", \"Yellow\", \"White\"], \"correct_answer\": \"Yellow\", \"explanation\": \"In additive colour mixing, combining red light and green light produces yellow light.\", \"reference_page\": 58, \"reference_section\": \"Formation of Secondary Colours by Colour Addition\"}, {\"question_number\": 16, \"question_type\": \"fill_in_blanks\", \"question_text\": \"Sound is defined as a form of energy carried by waves produced by __________ objects.\", \"correct_answer\": \"vibrating\", \"explanation\": \"The fundamental source of any sound is an object vibrating back and forth.\", \"reference_page\": 94, \"reference_section\": \"HOW SOUND IS PRODUCED\"}, {\"question_number\": 17, \"question_type\": \"fill_in_blanks\", \"question_text\": \"Sound waves propagating through air are classified as __________ waves because the particles of the medium vibrate parallel to the direction of wave travel.\", \"correct_answer\": \"longitudinal\", \"explanation\": \"Longitudinal waves are characterized by compressions and rarefactions, where particle motion is parallel to energy propagation, like sound in air.\", \"reference_page\": 96, \"reference_section\": \"SOUND AS LONGITUDINAL WAVES\"}, {\"question_number\": 18, \"question_type\": \"fill_in_blanks\", \"question_text\": \"The characteristic of a sound wave that determines its sharpness or shrillness, known as pitch, depends primarily on its __________.\", \"correct_answer\": \"frequency\", \"explanation\": \"Pitch is directly related to the frequency of the sound wave; higher frequency corresponds to higher pitch.\", \"reference_page\": 101, \"reference_section\": \"Pitch\"}, {\"question_number\": 19, \"question_type\": \"fill_in_blanks\", \"question_text\": \"The first law of reflection states that the incident ray, the reflected ray, and the __________ drawn at the point of incidence all lie in the same plane.\", \"correct_answer\": \"normal\", \"explanation\": \"The normal is the line perpendicular to the reflecting surface at the point where the incident ray strikes.\", \"reference_page\": 52, \"reference_section\": \"LAWS OF REFLECTION\"}, {\"question_number\": 20, \"question_type\": \"fill_in_blanks\", \"question_text\": \"For an object placed in front of a plane mirror, the image is formed __________ the mirror, and the image distance is equal to the object distance.\", \"correct_answer\": \"behind\", \"explanation\": \"Plane mirrors produce virtual images that appear to be located behind the mirror surface.\", \"reference_page\": 56, \"reference_section\": \"Characteristics of an Image formed by a Plane Mirror\"}, {\"question_number\": 21, \"question_type\": \"short_answer\", \"question_text\": \"Explain why sound requires a medium to travel and cannot propagate through a vacuum.\", \"correct_answer\": \"Sound travels as vibrations through particles of a medium (solid, liquid, or gas). These particles collide and transfer the vibration energy. A vacuum is devoid of particles, so there is nothing to vibrate and transmit the sound energy.\", \"reference_page\": 96, \"reference_section\": \"Propagation of Sound\"}, {\"question_number\": 22, \"question_type\": \"short_answer\", \"question_text\": \"What is the main difference between musical sound and noise in terms of the vibrations that produce them?\", \"correct_answer\": \"Musical sound is produced by regular, periodic vibrations and is generally pleasant to hear. Noise is produced by irregular, non-periodic vibrations and is typically unpleasant or unwanted.\", \"reference_page\": 100, \"reference_section\": \"TYPES OF SOUND\"}, {\"question_number\": 23, \"question_type\": \"short_answer\", \"question_text\": \"What does the acronym SONAR stand for, and mention one common application of this technology.\", \"correct_answer\": \"SONAR stands for Sound Navigation and Ranging. It is commonly used by ships and submarines to measure the depth of the sea, locate underwater objects like shipwrecks or submarines, or map the seabed.\", \"reference_page\": 104, \"reference_section\": \"SONAR\"}, {\"question_number\": 24, \"question_type\": \"short_answer\", \"question_text\": \"Explain the phenomenon of lateral inversion using the example of how the letter \'P\' would appear in a plane mirror.\", \"correct_answer\": \"Lateral inversion is the left-right reversal of an image in a plane mirror. If you hold up the letter \'P\' to a plane mirror, the image will look like \'q\'. The vertical line remains vertical, but the loop that is on the right side in the object appears on the left side in the image.\", \"reference_page\": 54, \"reference_section\": \"Lateral Inversion\"}, {\"question_number\": 25, \"question_type\": \"short_answer\", \"question_text\": \"Why does a blue object appear blue when illuminated by white light, but appear black when illuminated by red light?\", \"correct_answer\": \"A blue object appears blue in white light because it reflects blue light (which is part of white light) and absorbs other colours (like red, green, etc.). When illuminated by only red light, there is no blue light to reflect. Since it absorbs red light, it reflects almost no light and thus appears black.\", \"reference_page\": 59, \"reference_section\": \"APPEARANCE OF THE COLOUR OF AN OBJECT (BASED ON REFLECTION AND ABSORPTION)\"}, {\"question_number\": 26, \"question_type\": \"match_following\", \"question_text\": \"Match the sound wave characteristics in Column A with their descriptions or related concepts in Column B.\", \"options\": [\"Column A: 1. Amplitude\", \"Column A: 2. Frequency\", \"Column A: 3. Time Period\", \"Column A: 4. Wavelength\", \"Column A: 5. Pitch\", \"Column B: a. Number of vibrations per second (Hz)\", \"Column B: b. Time taken for one complete vibration (s)\", \"Column B: c. Maximum displacement from mean position (related to loudness)\", \"Column B: d. Distance between consecutive compressions or rarefactions (m)\", \"Column B: e. Perceptual property related to frequency (shrillness)\"], \"correct_answer\": [\"1-c\", \"2-a\", \"3-b\", \"4-d\", \"5-e\"], \"reference_page\": 99, \"reference_section\": \"TERMS RELATED TO A SOUND WAVE\"}, {\"question_number\": 27, \"question_type\": \"match_following\", \"question_text\": \"Match the type of sound or vibration in Column A with its corresponding frequency range or characteristic in Column B.\", \"options\": [\"Column A: 1. Infrasonic Sound\", \"Column A: 2. Audible Sound (Sonic)\", \"Column A: 3. Ultrasonic Sound\", \"Column A: 4. Musical Sound\", \"Column A: 5. Noise\", \"Column B: a. Produced by regular, periodic vibrations\", \"Column B: b. Produced by irregular, non-periodic vibrations\", \"Column B: c. Frequencies below 20 Hz\", \"Column B: d. Frequencies above 20,000 Hz\", \"Column B: e. Frequencies between 20 Hz and 20,000 Hz\"], \"correct_answer\": [\"1-c\", \"2-e\", \"3-d\", \"4-a\", \"5-b\"], \"reference_page\": 100, \"reference_section\": \"Audible and Inaudible Sounds / TYPES OF SOUND\"}, {\"question_number\": 28, \"question_type\": \"match_following\", \"question_text\": \"Match the terms related to reflection of light in Column A with their definitions in Column B.\", \"options\": [\"Column A: 1. Incident Ray\", \"Column A: 2. Reflected Ray\", \"Column A: 3. Normal\", \"Column A: 4. Angle of Incidence\", \"Column A: 5. Point of Incidence\", \"Column B: a. The ray of light bouncing back from the surface\", \"Column B: b. The point on the surface where the incident ray strikes\", \"Column B: c. The ray of light falling on the surface\", \"Column B: d. The angle between the incident ray and the normal\", \"Column B: e. A line drawn perpendicular to the surface at the point of incidence\"], \"correct_answer\": [\"1-c\", \"2-a\", \"3-e\", \"4-d\", \"5-b\"], \"reference_page\": 51, \"reference_section\": \"Terms Related to Reflection\"}, {\"question_number\": 29, \"question_type\": \"match_following\", \"question_text\": \"Match the characteristics of an image formed by a plane mirror (Column A) with their correct descriptions (Column B).\", \"options\": [\"Column A: 1. Image Type\", \"Column A: 2. Orientation\", \"Column A: 3. Relative Size\", \"Column A: 4. Position\", \"Column A: 5. Left-Right Reversal\", \"Column B: a. Same size as the object\", \"Column B: b. Image distance behind mirror equals object distance in front\", \"Column B: c. Virtual (cannot be formed on screen)\", \"Column B: d. Laterally inverted\", \"Column B: e. Upright (Erect)\"], \"correct_answer\": [\"1-c\", \"2-e\", \"3-a\", \"4-b\", \"5-d\"], \"reference_page\": 56, \"reference_section\": \"Characteristics of an Image formed by a Plane Mirror\"}, {\"question_number\": 30, \"question_type\": \"match_following\", \"question_text\": \"Match the colour mixing scenarios in Column A with the resulting colour in Column B (additive mixing of light).\", \"options\": [\"Column A: 1. Red Light + Green Light\", \"Column A: 2. Red Light + Blue Light\", \"Column A: 3. Blue Light + Green Light\", \"Column A: 4. Red + Green + Blue Light\", \"Column A: 5. Red Light + Cyan Light\", \"Column B: a. White Light\", \"Column B: b. Cyan Light\", \"Column B: c. Magenta Light\", \"Column B: d. Yellow Light\", \"Column B: e. White Light (Complementary colours)\"], \"correct_answer\": [\"1-d\", \"2-c\", \"3-b\", \"4-a\", \"5-e\"], \"reference_page\": 58, \"reference_section\": \"Formation of Secondary Colours by Colour Addition / COMPLEMENTARY COLOURS\"}, {\"question_number\": 31, \"question_type\": \"single_select\", \"question_text\": \"Sound can travel through a vacuum.\", \"options\": [\"True\", \"False\"], \"correct_answer\": \"False\", \"explanation\": \"Sound requires a medium (particles) to propagate; a vacuum lacks particles.\", \"reference_page\": 96, \"reference_section\": \"Propagation of Sound\"}, {\"question_number\": 32, \"question_type\": \"single_select\", \"question_text\": \"The loudness of a sound primarily depends on its frequency.\", \"options\": [\"True\", \"False\"], \"correct_answer\": \"False\", \"explanation\": \"Loudness is primarily determined by the amplitude of the sound wave, while frequency determines the pitch.\", \"reference_page\": 99, \"reference_section\": \"TERMS RELATED TO A SOUND WAVE / Pitch\"}, {\"question_number\": 33, \"question_type\": \"single_select\", \"question_text\": \"In a plane mirror, the image formed is always real and inverted.\", \"options\": [\"True\", \"False\"], \"correct_answer\": \"False\", \"explanation\": \"A plane mirror forms a virtual, upright, and laterally inverted image.\", \"reference_page\": 56, \"reference_section\": \"Characteristics of an Image formed by a Plane Mirror\"}, {\"question_number\": 34, \"question_type\": \"single_select\", \"question_text\": \"The law stating that the angle of incidence equals the angle of reflection applies only to regular reflection from smooth surfaces.\", \"options\": [\"True\", \"False\"], \"correct_answer\": \"False\", \"explanation\": \"The law of reflection (angle i = angle r) applies to all types of reflection, including diffuse reflection from rough surfaces. The difference is that parallel incident rays are scattered in diffuse reflection.\", \"reference_page\": 52, \"reference_section\": \"LAWS OF REFLECTION\"}, {\"question_number\": 35, \"question_type\": \"single_select\", \"question_text\": \"Mixing beams of blue light and yellow light will produce white light.\", \"options\": [\"True\", \"False\"], \"correct_answer\": \"True\", \"explanation\": \"Blue and yellow are complementary colours in additive light mixing. Yellow light is a mixture of red and green light, so mixing blue with yellow (red+green) effectively mixes red, green, and blue light, which produces white light.\", \"reference_page\": 58, \"reference_section\": \"COMPLEMENTARY COLOURS\"}]',1);
/*!40000 ALTER TABLE `assessments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assignment_format_questions`
--

DROP TABLE IF EXISTS `assignment_format_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignment_format_questions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `assignment_format_id` int(11) NOT NULL,
  `question_type` varchar(50) NOT NULL,
  `count` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_assignment_format_question_type` (`assignment_format_id`,`question_type`),
  KEY `ix_assignment_format_questions_id` (`id`),
  KEY `ix_assignment_format_questions_assignment_format_id` (`assignment_format_id`),
  CONSTRAINT `assignment_format_questions_ibfk_1` FOREIGN KEY (`assignment_format_id`) REFERENCES `assignment_formats` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_assignment_format_question_count_non_negative` CHECK (`count` >= 0)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignment_format_questions`
--

LOCK TABLES `assignment_format_questions` WRITE;
/*!40000 ALTER TABLE `assignment_format_questions` DISABLE KEYS */;
INSERT INTO `assignment_format_questions` VALUES
(1,1,'single_select',10),
(2,1,'fill_in_blanks',5),
(3,1,'short_answer',5),
(4,1,'match_following',1);
/*!40000 ALTER TABLE `assignment_format_questions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assignment_formats`
--

DROP TABLE IF EXISTS `assignment_formats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignment_formats` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `created_by_user_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `ix_assignment_formats_id` (`id`),
  KEY `ix_assignment_formats_created_by_user_id` (`created_by_user_id`),
  CONSTRAINT `assignment_formats_ibfk_1` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignment_formats`
--

LOCK TABLES `assignment_formats` WRITE;
/*!40000 ALTER TABLE `assignment_formats` DISABLE KEYS */;
INSERT INTO `assignment_formats` VALUES
(1,'Physics Term 1',2,'2025-04-15 17:45:09','2025-04-15 17:45:09');
/*!40000 ALTER TABLE `assignment_formats` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assignment_sample_url_association`
--

DROP TABLE IF EXISTS `assignment_sample_url_association`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignment_sample_url_association` (
  `assignment_sample_id` int(11) NOT NULL,
  `url_id` int(11) NOT NULL,
  PRIMARY KEY (`assignment_sample_id`,`url_id`),
  KEY `url_id` (`url_id`),
  CONSTRAINT `assignment_sample_url_association_ibfk_1` FOREIGN KEY (`assignment_sample_id`) REFERENCES `assignment_samples` (`id`) ON DELETE CASCADE,
  CONSTRAINT `assignment_sample_url_association_ibfk_2` FOREIGN KEY (`url_id`) REFERENCES `urls` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignment_sample_url_association`
--

LOCK TABLES `assignment_sample_url_association` WRITE;
/*!40000 ALTER TABLE `assignment_sample_url_association` DISABLE KEYS */;
INSERT INTO `assignment_sample_url_association` VALUES
(1,5),
(1,6);
/*!40000 ALTER TABLE `assignment_sample_url_association` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `assignment_samples`
--

DROP TABLE IF EXISTS `assignment_samples`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `assignment_samples` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `subject_id` int(11) NOT NULL,
  `created_by_user_id` int(11) DEFAULT NULL,
  `file_size` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_assignment_samples_subject_id` (`subject_id`),
  KEY `ix_assignment_samples_id` (`id`),
  KEY `ix_assignment_samples_created_by_user_id` (`created_by_user_id`),
  CONSTRAINT `assignment_samples_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `assignment_samples_ibfk_2` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `assignment_samples`
--

LOCK TABLES `assignment_samples` WRITE;
/*!40000 ALTER TABLE `assignment_samples` DISABLE KEYS */;
INSERT INTO `assignment_samples` VALUES
(1,'Physics qp ','Physics qp',1,2,1094007,'2025-04-15 17:39:44','2025-04-15 17:39:47');
/*!40000 ALTER TABLE `assignment_samples` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `timestamp` datetime DEFAULT current_timestamp(),
  `user_id` int(11) DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `target_entity` varchar(50) DEFAULT NULL,
  `target_entity_id` int(11) DEFAULT NULL,
  `details` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_audit_logs_user_id` (`user_id`),
  KEY `ix_audit_logs_timestamp` (`timestamp`),
  KEY `ix_audit_logs_target_entity_id` (`target_entity_id`),
  KEY `ix_audit_logs_id` (`id`),
  KEY `ix_audit_logs_action` (`action`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `audit_logs`
--

LOCK TABLES `audit_logs` WRITE;
/*!40000 ALTER TABLE `audit_logs` DISABLE KEYS */;
INSERT INTO `audit_logs` VALUES
(1,'2025-04-15 17:31:56',1,'USER_LOGIN','User',1,'User \'admin\' logged in successfully.'),
(2,'2025-04-15 17:33:44',1,'USER_LOGIN','User',1,'User \'admin\' logged in successfully.'),
(3,'2025-04-15 17:36:45',2,'USER_LOGIN','User',2,'User \'kousir\' logged in successfully.'),
(4,'2025-04-15 17:39:47',2,'ASSIGNMENT_SAMPLE_CREATED','AssignmentSample',1,'User \'kousir\' created assignment sample \'Physics qp \' (ID: 1) for Subject ID 1.'),
(5,'2025-04-15 17:40:38',2,'ASSIGNMENT_SAMPLE_ANALYZED','AssignmentSample',1,'User \'kousir\' triggered AI analysis for assignment sample \'Physics qp \' (ID: 1). Result: {\'question_counts\': [{\'type\': <QuestionTypeEnum.SINGLE_SELECT: \'single_select\'>, \'count\': 15}, {\'type\': <QuestionTypeEnum.FILL_IN_BLANKS: \'fill_in_blanks\'>, \'count\': 5}, {\'type\': <QuestionTypeEnum.SHORT_ANSWER: \'short_answer\'>, \'count\': 26}, {\'type\': <QuestionTypeEnum.MATCH_FOLLOWING: \'match_following\'>, \'count\': 1}]}'),
(6,'2025-04-15 17:45:09',2,'ASSIGNMENT_FORMAT_CREATED','AssignmentFormat',1,'User \'kousir\' created format \'Physics Term 1\' (ID: 1).'),
(7,'2025-04-15 17:48:48',2,'ASSESSMENT_DEFINITION_CREATED','Assessment',1,'User \'kousir\' created assessment definition \'Physics Assignment Term 2025 - 1\' (ID: 1). Linked lessons: [1].'),
(8,'2025-04-15 17:56:44',2,'USER_LOGIN','User',2,'User \'kousir\' logged in successfully.');
/*!40000 ALTER TABLE `audit_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `grades`
--

DROP TABLE IF EXISTS `grades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `grades` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_grades_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `grades`
--

LOCK TABLES `grades` WRITE;
/*!40000 ALTER TABLE `grades` DISABLE KEYS */;
INSERT INTO `grades` VALUES
(1,'7th Grade');
/*!40000 ALTER TABLE `grades` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `images`
--

DROP TABLE IF EXISTS `images`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `images` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `pdf_id` int(11) DEFAULT NULL,
  `image_number` int(11) DEFAULT NULL,
  `page_number` int(11) DEFAULT NULL,
  `chapter_number` int(11) DEFAULT NULL,
  `url_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `pdf_id` (`pdf_id`),
  KEY `url_id` (`url_id`),
  KEY `ix_images_id` (`id`),
  CONSTRAINT `images_ibfk_1` FOREIGN KEY (`pdf_id`) REFERENCES `pdfs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `images_ibfk_2` FOREIGN KEY (`url_id`) REFERENCES `urls` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `images`
--

LOCK TABLES `images` WRITE;
/*!40000 ALTER TABLE `images` DISABLE KEYS */;
/*!40000 ALTER TABLE `images` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `lessons`
--

DROP TABLE IF EXISTS `lessons`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `lessons` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `subject_id` int(11) NOT NULL,
  `term_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `subject_id` (`subject_id`),
  KEY `term_id` (`term_id`),
  KEY `ix_lessons_id` (`id`),
  CONSTRAINT `lessons_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `lessons_ibfk_2` FOREIGN KEY (`term_id`) REFERENCES `terms` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lessons`
--

LOCK TABLES `lessons` WRITE;
/*!40000 ALTER TABLE `lessons` DISABLE KEYS */;
INSERT INTO `lessons` VALUES
(1,'Light',1,1),
(2,'Sound',1,1);
/*!40000 ALTER TABLE `lessons` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parent_student_association`
--

DROP TABLE IF EXISTS `parent_student_association`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `parent_student_association` (
  `parent_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  PRIMARY KEY (`parent_id`,`student_id`),
  KEY `student_id` (`student_id`),
  CONSTRAINT `parent_student_association_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `parents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `parent_student_association_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parent_student_association`
--

LOCK TABLES `parent_student_association` WRITE;
/*!40000 ALTER TABLE `parent_student_association` DISABLE KEYS */;
/*!40000 ALTER TABLE `parent_student_association` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parents`
--

DROP TABLE IF EXISTS `parents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `parents` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `ix_parents_id` (`id`),
  CONSTRAINT `parents_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parents`
--

LOCK TABLES `parents` WRITE;
/*!40000 ALTER TABLE `parents` DISABLE KEYS */;
/*!40000 ALTER TABLE `parents` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pdf_urls`
--

DROP TABLE IF EXISTS `pdf_urls`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pdf_urls` (
  `pdf_id` int(11) NOT NULL,
  `url_id` int(11) NOT NULL,
  PRIMARY KEY (`pdf_id`,`url_id`),
  KEY `url_id` (`url_id`),
  CONSTRAINT `pdf_urls_ibfk_1` FOREIGN KEY (`pdf_id`) REFERENCES `pdfs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `pdf_urls_ibfk_2` FOREIGN KEY (`url_id`) REFERENCES `urls` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pdf_urls`
--

LOCK TABLES `pdf_urls` WRITE;
/*!40000 ALTER TABLE `pdf_urls` DISABLE KEYS */;
INSERT INTO `pdf_urls` VALUES
(1,1),
(1,2),
(2,3),
(2,4);
/*!40000 ALTER TABLE `pdf_urls` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pdfs`
--

DROP TABLE IF EXISTS `pdfs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `pdfs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `lesson_id` int(11) DEFAULT NULL,
  `size` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lesson_id` (`lesson_id`),
  KEY `ix_pdfs_id` (`id`),
  CONSTRAINT `pdfs_ibfk_1` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pdfs`
--

LOCK TABLES `pdfs` WRITE;
/*!40000 ALTER TABLE `pdfs` DISABLE KEYS */;
INSERT INTO `pdfs` VALUES
(1,'Light',1,4662934),
(2,'Sound',2,4220844);
/*!40000 ALTER TABLE `pdfs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sections`
--

DROP TABLE IF EXISTS `sections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sections` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `grade_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `grade_id` (`grade_id`),
  KEY `ix_sections_id` (`id`),
  CONSTRAINT `sections_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sections`
--

LOCK TABLES `sections` WRITE;
/*!40000 ALTER TABLE `sections` DISABLE KEYS */;
/*!40000 ALTER TABLE `sections` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_assessment_scores`
--

DROP TABLE IF EXISTS `student_assessment_scores`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_assessment_scores` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `student_id` int(11) NOT NULL,
  `assessment_id` int(11) NOT NULL,
  `term_id` int(11) NOT NULL,
  `score_achieved` float NOT NULL,
  `max_score` float NOT NULL,
  `attempt_timestamp` datetime DEFAULT current_timestamp(),
  `comments` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `student_id` (`student_id`),
  KEY `assessment_id` (`assessment_id`),
  KEY `term_id` (`term_id`),
  KEY `ix_student_assessment_scores_id` (`id`),
  CONSTRAINT `student_assessment_scores_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_assessment_scores_ibfk_2` FOREIGN KEY (`assessment_id`) REFERENCES `assessments` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_assessment_scores_ibfk_3` FOREIGN KEY (`term_id`) REFERENCES `terms` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_assessment_scores`
--

LOCK TABLES `student_assessment_scores` WRITE;
/*!40000 ALTER TABLE `student_assessment_scores` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_assessment_scores` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `student_years`
--

DROP TABLE IF EXISTS `student_years`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_years` (
  `studentId` int(11) NOT NULL,
  `year` int(11) NOT NULL,
  `sectionId` int(11) DEFAULT NULL,
  PRIMARY KEY (`studentId`,`year`),
  KEY `sectionId` (`sectionId`),
  CONSTRAINT `student_years_ibfk_1` FOREIGN KEY (`studentId`) REFERENCES `students` (`id`) ON DELETE CASCADE,
  CONSTRAINT `student_years_ibfk_2` FOREIGN KEY (`sectionId`) REFERENCES `sections` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `student_years`
--

LOCK TABLES `student_years` WRITE;
/*!40000 ALTER TABLE `student_years` DISABLE KEYS */;
/*!40000 ALTER TABLE `student_years` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `ix_students_id` (`id`),
  CONSTRAINT `students_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `students`
--

LOCK TABLES `students` WRITE;
/*!40000 ALTER TABLE `students` DISABLE KEYS */;
/*!40000 ALTER TABLE `students` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `subjects`
--

DROP TABLE IF EXISTS `subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `subjects` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `grade_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `grade_id` (`grade_id`),
  KEY `ix_subjects_id` (`id`),
  CONSTRAINT `subjects_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `subjects`
--

LOCK TABLES `subjects` WRITE;
/*!40000 ALTER TABLE `subjects` DISABLE KEYS */;
INSERT INTO `subjects` VALUES
(1,'Physics',1);
/*!40000 ALTER TABLE `subjects` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `teachers`
--

DROP TABLE IF EXISTS `teachers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `teachers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `ix_teachers_id` (`id`),
  CONSTRAINT `teachers_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `teachers`
--

LOCK TABLES `teachers` WRITE;
/*!40000 ALTER TABLE `teachers` DISABLE KEYS */;
INSERT INTO `teachers` VALUES
(1,'kousir',2);
/*!40000 ALTER TABLE `teachers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `terms`
--

DROP TABLE IF EXISTS `terms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `terms` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `year` int(11) NOT NULL,
  `grade_id` int(11) NOT NULL,
  `start_date` date DEFAULT NULL,
  `end_date` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_term_name_year_grade` (`name`,`year`,`grade_id`),
  KEY `grade_id` (`grade_id`),
  KEY `ix_terms_year` (`year`),
  KEY `ix_terms_id` (`id`),
  CONSTRAINT `terms_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `terms`
--

LOCK TABLES `terms` WRITE;
/*!40000 ALTER TABLE `terms` DISABLE KEYS */;
INSERT INTO `terms` VALUES
(1,'Term 1',2025,1,'2025-04-15','2025-04-15');
/*!40000 ALTER TABLE `terms` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `timetables`
--

DROP TABLE IF EXISTS `timetables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `timetables` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `day_of_week` int(11) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `section_id` int(11) NOT NULL,
  `subject_id` int(11) NOT NULL,
  `teacher_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_timetable_day_start_section` (`day_of_week`,`start_time`,`section_id`),
  UNIQUE KEY `uq_timetable_day_end_section` (`day_of_week`,`end_time`,`section_id`),
  KEY `teacher_id` (`teacher_id`),
  KEY `ix_timetables_section_id` (`section_id`),
  KEY `ix_timetables_id` (`id`),
  KEY `ix_timetables_subject_id` (`subject_id`),
  KEY `ix_timetables_day_of_week` (`day_of_week`),
  CONSTRAINT `timetables_ibfk_1` FOREIGN KEY (`section_id`) REFERENCES `sections` (`id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_3` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `timetables`
--

LOCK TABLES `timetables` WRITE;
/*!40000 ALTER TABLE `timetables` DISABLE KEYS */;
/*!40000 ALTER TABLE `timetables` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `urls`
--

DROP TABLE IF EXISTS `urls`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `urls` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url` varchar(255) DEFAULT NULL,
  `url_type` varchar(5) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_urls_id` (`id`),
  CONSTRAINT `chk_url_type_values` CHECK (`url_type` in ('https','gs'))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `urls`
--

LOCK TABLES `urls` WRITE;
/*!40000 ALTER TABLE `urls` DISABLE KEYS */;
INSERT INTO `urls` VALUES
(1,'https://storage.googleapis.com/lms-ai/pdfs/1.pdf','https'),
(2,'gs://lms-ai/pdfs/1.pdf','gs'),
(3,'https://storage.googleapis.com/lms-ai/pdfs/2.pdf','https'),
(4,'gs://lms-ai/pdfs/2.pdf','gs'),
(5,'https://storage.googleapis.com/lms-ai/assignments_pdfs/1.pdf','https'),
(6,'gs://lms-ai/assignments_pdfs/1.pdf','gs');
/*!40000 ALTER TABLE `urls` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) DEFAULT NULL,
  `user_type` varchar(20) NOT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `last_login` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_users_username` (`username`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES
(1,'admin','admin@example.com','$2b$12$WofojNbsiCmELgmExBz0D.aLla5l3GI9BQwEXjR3FYeBmWxO1O3gO','Admin',1,'','2025-04-15 17:31:30','2025-04-15 17:33:44'),
(2,'kousir','kousir@gmail.com','$2b$12$ETrsA9Bh1YKcBWdLg5qq4uhWflmqSlJOEc1GBqtwHNweV5yYRlJJK','Teacher',1,'https://storage.googleapis.com/lms-ai/users/2.png','2025-04-15 17:36:19','2025-04-15 17:56:44');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `videos`
--

DROP TABLE IF EXISTS `videos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `videos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `lesson_id` int(11) DEFAULT NULL,
  `url_id` int(11) DEFAULT NULL,
  `size` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lesson_id` (`lesson_id`),
  KEY `url_id` (`url_id`),
  KEY `ix_videos_id` (`id`),
  CONSTRAINT `videos_ibfk_1` FOREIGN KEY (`lesson_id`) REFERENCES `lessons` (`id`) ON DELETE CASCADE,
  CONSTRAINT `videos_ibfk_2` FOREIGN KEY (`url_id`) REFERENCES `urls` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `videos`
--

LOCK TABLES `videos` WRITE;
/*!40000 ALTER TABLE `videos` DISABLE KEYS */;
/*!40000 ALTER TABLE `videos` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-04-16 11:29:26
