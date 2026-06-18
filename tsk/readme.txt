The date that this table of contents was created is: 06/28/2011

You have selected to download the TSK (Treasury of Scripture Knowledge). The files included in the downloads are geared to
computer application developers who want to leverage this data into an application they support or wish to build.


Here is a list of the file(s) found in this .zip file:
1.) tskxref.txt - TAB delimited text file. Each line represents a TSK entry associated with a verse.  It is terminated by 
                  a carriage return. 

Here is the structure for the file:

+----------------+---------------+
| Field          | Type          |
+----------------+---------------+
| book_key       | integer       | -> represents the key to the book
| chapter_nbr    | integer       | -> represents the chapter number within the book
| verse_nbr      | integer       | -> represents the verse number within the chapter
| sort_order     | integer       | -> represents the order in which the word should be displayed
| word           | varchar(2028) | -> the TSK word or phrase
| reference_list | varchar(4096) | -> a list of all of the references (in lowercase) that the TSK entry points to.
+----------------+---------------+    abbreviations are used to denote a book (see below for complete list).  all
                                      references are delimited by a semi-colon.
                                      
What follows is a list of the book_key assignments.  All deuterocanonical books numbering begin after Revelation's book 
number assignment.  

+----------+-----------------+
| book_key | book name       |
+----------+-----------------+
|        1 | Genesis         |
|        2 | Exodus          |
|        3 | Leviticus       |
|        4 | Numbers         |
|        5 | Deuteronomy     |
|        6 | Joshua          |
|        7 | Judges          |
|        8 | Ruth            |
|        9 | 1 Samuel        |
|       10 | 2 Samuel        |
|       11 | 1 Kings         |
|       12 | 2 Kings         |
|       13 | 1 Chronicles    |
|       14 | 2 Chronicles    |
|       15 | Ezra            |
|       16 | Nehemiah        |
|       17 | Esther          |
|       18 | Job             |
|       19 | Psalms          |
|       20 | Proverbs        |
|       21 | Ecclesiates     |
|       22 | Song of Solomon |
|       23 | Isaiah          |
|       24 | Jeremiah        |
|       25 | Lamentations    |
|       26 | Ezekiel         |
|       27 | Daniel          |
|       28 | Hosea           |
|       29 | Joel            |
|       30 | Amos            |
|       31 | Obadiah         |
|       32 | Jonah           |
|       33 | Micah           |
|       34 | Nahum           |
|       35 | Habakkuk        |
|       36 | Zephaniah       |
|       37 | Haggi           |
|       38 | Zechariah       |
|       39 | Malachi         |
|       40 | Matthew         |
|       41 | Mark            |
|       42 | Luke            |
|       43 | John            |
|       44 | Acts            |
|       45 | Romans          |
|       46 | 1 Corinthians   |
|       47 | 2 Corinthians   |
|       48 | Galatians       |
|       49 | Ephesians       |
|       50 | Philippians     |
|       51 | Colossians      |
|       52 | 1 Thessalonians |
|       53 | 2 Thessalonians |
|       54 | 1 Timothy       |
|       55 | 2 Timothy       |
|       56 | Titus           |
|       57 | Philemon        |
|       58 | Hebrews         |
|       59 | James           |
|       60 | 1 Peter         |
|       61 | 2 Peter         |
|       62 | 1 John          |
|       63 | 2 John          |
|       64 | 3 John          |
|       65 | Jude            |
|       66 | Revelation      |
+----------+-----------------+

Abbreviations are used for references.  Here is the list:

+----------+-----------------+--------+
| book_key | name            | abbrev |
+----------+-----------------+--------+
|        1 | Genesis         | ge     | 
|        2 | Exodus          | ex     | 
|        3 | Leviticus       | le     | 
|        4 | Numbers         | nu     | 
|        5 | Deuteronomy     | de     | 
|        6 | Joshua          | jos    | 
|        7 | Judges          | jud    | 
|        8 | Ruth            | ru     | 
|        9 | 1 Samuel        | 1sa    | 
|       10 | 2 Samuel        | 2sa    | 
|       11 | 1 Kings         | 1ki    | 
|       12 | 2 Kings         | 2ki    | 
|       13 | 1 Chronicles    | 1ch    | 
|       14 | 2 Chronicles    | 2ch    | 
|       15 | Ezra            | ezr    | 
|       16 | Nehemiah        | ne     | 
|       17 | Esther          | es     | 
|       18 | Job             | job    | 
|       19 | Psalms          | ps     | 
|       20 | Proverbs        | pr     | 
|       21 | Ecclesiates     | ec     | 
|       22 | Song of Solomon | so     | 
|       23 | Isaiah          | isa    | 
|       24 | Jeremiah        | jer    | 
|       25 | Lamentations    | la     | 
|       26 | Ezekiel         | eze    | 
|       27 | Daniel          | da     | 
|       28 | Hosea           | ho     | 
|       29 | Joel            | joe    | 
|       30 | Amos            | am     | 
|       31 | Obadiah         | ob     | 
|       32 | Jonah           | jon    | 
|       33 | Micah           | mic    | 
|       34 | Nahum           | na     | 
|       35 | Habakkuk        | hab    | 
|       36 | Zephaniah       | zep    | 
|       37 | Haggi           | hag    | 
|       38 | Zechariah       | zec    | 
|       39 | Malachi         | mal    | 
|       40 | Matthew         | mt     | 
|       41 | Mark            | mr     | 
|       42 | Luke            | lu     | 
|       43 | John            | joh    | 
|       44 | Acts            | ac     | 
|       45 | Romans          | ro     | 
|       46 | 1 Corinthians   | 1co    | 
|       47 | 2 Corinthians   | 2co    | 
|       48 | Galatians       | ga     | 
|       49 | Ephesians       | eph    | 
|       50 | Philippians     | php    | 
|       51 | Colossians      | col    | 
|       52 | 1 Thessalonians | 1th    | 
|       53 | 2 Thessalonians | 2th    | 
|       54 | 1 Timothy       | 1ti    | 
|       55 | 2 Timothy       | 2ti    | 
|       56 | Titus           | tit    | 
|       57 | Philemon        | phm    | 
|       58 | Hebrews         | heb    | 
|       59 | James           | jas    | 
|       60 | 1 Peter         | 1pe    | 
|       61 | 2 Peter         | 2pe    | 
|       62 | 1 John          | 1jo    | 
|       63 | 2 John          | 2jo    | 
|       64 | 3 John          | 3jo    | 
|       65 | Jude            | jude   | 
|       66 | Revelation      | re     | 
+----------+-----------------+--------+

Best wishes! I hope you find an interesting way to work with this data!

here is example text:

countries, and in their nations.	ge 10:6;ge 11:1-9
1	10	21	1	the father	ge 11:10-26
1	10	21	2	Eber	nu 24:24
1	10	22	1	children	ge 9:26;1ch 1:17-27
1	10	22	2	Elam	ge 14:1-9;2ki 15:19;job 1:17;isa 11:11;isa 21:2;isa 22:6;jer 25:25;jer 49:34-39;ac 2:9
1	10	22	3	Lud	isa 66:19
1	10	22	4	Aram	nu 23:7
1	10	23	1	Uz	job 1:1;jer 25:20
1	10	24	1	Salah	ge 11:12-15
1	10	25	1	A. M. 1757. B.C. 2247. Eber	ge 10:21;1ch 1:19
1	10	25	2	the name	ge 11:16-19;lu 3:35,36
1	10	25	3	in	ge 10:32;de 32:8;ac 17:26
1	10	26	1	And Joktan begat Almodad, and Sheleph, and Hazarmaveth, and Jerah,	1ch 1:20-28
1	10	27	1	And Hadoram, and Uzal, and Diklah,	1ch 1:20-28
1	10	28	1	And Obal, and Abimael, and Sheba,	ge 25:3;1ki 10:1;1ch 1:20-28
1	10	29	1	Ophir	1ki 9:28;1ki 22:48;1ch 8:18;1ch 9:10,13;job 22:24;job 28:16;ps 45:9;isa 13:12
1	10	29	2	Havilah	ge 2:11;ge 25:18;1sa 15:7
1	10	30	1	mount of the east	nu 23:7
1	10	31	1	These are the sons of Shem, after their families, after their tongues, in their lands, after their nations.	ge 10:5,20;ac 17:26
1	10	32	1	are the	ge 10:1,20,31;ge 5:29-31
1	10	32	2	nations	ge 10:25;ge 9:1,7,19;ac 17:26
1	11	1	3	A. M. 1757. B.C. 2247. was	isa 19:18;zep 3:9;ac 2:6