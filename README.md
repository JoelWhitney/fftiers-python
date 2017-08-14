This program was inspired by the work already done by Boris Chen (http://www.borischen.co/)

Read more about his work here:
www.nytimes.com/2013/10/11/sports/football/turning-advanced-statistics-into-fantasy-football-analysis.html

See his initial work here:
https://github.com/borisachen/fftiers


**Overview**

This code is tested using Python 3.4. Some additional libraries will need to be installed for the code to run properly

A clustering program that uses FantasyPros data inspired by Boris Chen (http://www.borischen.co/)
This program utilizes unsupervised machine learning by flat clustering with KMeans -- a simple way
to uncover like tiers within the player data mined from FantasyPros (http://www.fantasypros.com/)

**To run**

Run from command line

Note: The token can be found by searching the FantasyPros Login page source for 'csrfmiddlewaretoken'

`cd "<directory_python_file>" && py -3 "ff-tiers.py" -u "<FantasyPros_username>" -p "<FantasyPros_password>" -t "<FantasyPros_token>"`
`cd "/Users/joel8641/Box Sync/Projects/GitHub/fftiers-python/src" && py -3 "ff-tiers.py" -u "whitneyjb5" -p "999jbw" -t "reiHrx0n5o7YstOIFsZ5Gj29UVuuC80z"`
`cd "/Users/joel8641/Box Sync/Projects/GitHub/fftiers-python/src" && python3.5 "ff-tiers.py" -u "whitneyjb5" -p "999jbw" -t "reiHrx0n5o7YstOIFsZ5Gj29UVuuC80z"`


**To do**
- Output to CSV with tiers
- Add sms alert when graph updated (pass/fail)
- Make the script run continuously once a day
  - cPanel in cgi?
  - from Raspberry Pi
    - upload to site from here?
  - Add local v auto run option
    - once v timed runtime
- Make this program work with NHL data for Fantasy Hockey