# Weblate
Scripts related to translation of the LibreOffice user interface, "help", and other files LibreOffice translates using the [Weblate](https://weblate.org) tool.

`potrans.py`: download, export to CSV, check, modify and upload LibreOffice translations maintained at the [LibreOffice Weblate server](https://translations.documentfoundation.org/)

`dialogtrans.py`: render translated LibreOffice dialogs.

# potrans.py
A script to download, modify and upload LibreOffice translation subprojects (in Weblate called *slugs*) from the [LibreOffice Weblate server](https://translations.documentfoundation.org/) by means of the Weblate's API.

On download the script creates a directory with two copies of each subproject's PO file. One of them, starting with a dot, is in Linux not visible in regular file view and serves as a backup, for example to cancel current changes.

Currently the following sub-projects are supported:
* 'help': "libo_help-master",
* 'ui': "libo_ui-master",
* 'ui70': "libo_ui-7-0",
* 'ui64': "libo_ui-6-4",
* 'ui63': "libo_ui-6-3"

Abbreviations on the left are shortcuts used in the script commands. The slug names on the right are used as directory names.

Using the Weblate's web interface one translates the 'master' sub-projects and translations are propagated to other related sub-projects (libo_ui-master > libo_ui-7-0 etc.). This does not work when uploading PO files using the Weblate's API, so one has to transfer translations between subprojects using this script (libo_ui-master > libo_ui-7-0 etc.) and then upload them separately.

## Using the script
### Operating system and dependencies
The script was developed and tested in a Linux environment using Python 3. The scenarios described below may also require other Linux specific tools.

It is likely that the script and related tools work equally well in WSL ([Windows subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10)).

### Run the Script
The scripts has switches and commands and should be run this way:

`potrans.py switches command`

for example, `potrans.py -h` displays a help.

### Switches
Some switches apply to all commands, some switches are command specific.

Common switches are:

```
-h                This usage
-w site           Weblate site URL {taken from the WEBLATE_API_SITE environment variable}
-p project        Abbreviation of Weblate's subproject (slug) ['help', 'ui', 'ui70', 'ui64', 'ui63']
-k key            Weblate account key {taken from the WEBLATE_API_KEY environment variable}
-l lang_code      Language code {taken from the WEBLATE_API_LANG environment variable}

```

When using `bash`, set the environment variables in the `.bashrc` file:
```
export WEBLATE_API_SITE=https://translations.documentfoundation.org/api/
export WEBLATE_API_KEY=vt6ttvT6t9T976t&^t76T76vt^tv7^Tv76tV6tv6t
export WEBLATE_API_LANG=sk
```
You can find your key in Weblate's GUI [Settings](https://translations.documentfoundation.org/accounts/profile/#api) (Your profile > Settings > API Access, the icon in the upper right corner).

Commands and their specific switches are described below. We assume language is set to `sk`. Commands can be abbreviated to usually 2 letters.

## Download a subproject

`potrans.py -p ui download ` (default language: `sk`, taken from environment)

`potrans.py -p ui -l cz download ` (with specified language, in this case `cz`)

Downloads the `ui` subproject, creates directory `libo_ui-master/lang_code` with the PO files.

Downloading individual files may fail. Usually a failure is detected and downloading restarted. Sometimes, however, downloading hangs. If so, abort the script (CRTL+C) and restart it. Already downloaded PO files will be skipped.

In order to re-download currently downloaded translation files, use the `-d` switch:
```
potrans.py -p ui -d download
``` 
If a list of translation files on the server changes, it is necessary to delete the component (e.g. `libo_ui-master/sk)`and download it again.

## Upload a subproject

`potrans.py -p ui upload ` (default language: `sk`)

`potrans.py -p ui -l cz upload ` (with specified language, in this case `cz`)

## View current changes
`potrans.py -p ui modified` lists modified files

`potrans.py -p ui diff` lists differences, for example:

```
Differences in  libo_ui-master/sk/sc/messages.po:
	_Show changes in spreadsheet```
       < _Zobraziť zmeny v zošite
	   > _Zobraziť zmeny v hárku
```
The line marked by `<` is the original, the one marked by `>` is the new version.

## Cancel current changes
`potrans.py -p ui reset`
All changes will be cancelled to the download state.

## Remove a subproject
Use system tools, e.g.:

`rm -rf libo_ui-master`

or

`rm -rf libo_ui-master/sk`

to remove only the `sk` language.

## Normalize string ending characters
Quite often a source string and translated string end with a different character. Weblate can detect some of these inconsistencies and lists them in the `Checks` column. They need to be fixed one-by-one, which is cumbersome.

To fix the problem, run
```
potrans.py -p ui fixchar
```
The command also removes double-spaces and removes spaces before the `,` and `.`.

For example (run `potrans.py -p ui diff` to display changes):
```
'Line Spacing:'
	< 'Riadkovanie'
	> 'Riadkovanie:'
```
or
```
'Specifies additional sorting criteria. You can also combine sort keys.'
	< 'Určuje ďalšie kritériá zoraďovania. Zoraďovacie kľúče môžete kombinovať .'
	> 'Určuje ďalšie kritériá zoraďovania. Zoraďovacie kľúče môžete kombinovať.'
```
## Export glossary
A two column "Source<TAB>Translation" CSV file is exported. It can be used, e.g., in OmegaT as a glossary (OmegaT then offers translation suggestions for substrings of a translated string equal to GUI items):
```
potrans -p ui glossary > output.csv
```
To use the glossary file in OmegaT, copy the resulting CSV file to OmegaT's working directory (the 'glossary' subdirectory). It is necessary to change suffix of the file to `.txt`.

Length of the output messages can be limited by the `-m` switch:
```
potrans -p ui -m 70 glossary > output.csv
```
Multiline messages are not exported.

## Export translations
The goal is to export translated and/or untranslated messages to a CSV file, which can be translated and imported back, used to find typos and translation conflicts, or perhaps for other purposes.

A CSV file with 4 tab-separated columns is exported:
`File name <TAB> KeyID <TAB> Source <TAB> Target`, for example:
```
libo_ui-master/sk/avmedia/messages.po	yTBHR	200%	200 %
```

The newline characters are replaced by a placeholder <LINE_BREAK> to enable processing with programs which do not understand the structure of CSV files. These are reverted to the newline character upon import.

To export translations run
```
potrans -p ui {switches} export > output.csv
```
Possible export types are specified by switches:

`-u`: Only export untranslated messages

`-f`: Only export conflicting translations (different translations for one source string)

`-r`: Only export conflicting translations (reversed, two or several different source strings for one translation string)

`-g`: Export translations with inconsistent tags

`-t`: Only export extended tooltips (they contain the tag <ahelp> in help and word 'extended' in entry.msgctxt in ui). May be combined with the -f and -r switches.

`-i`: Only export strings with conflicting translation of UI substrings. UI substrings are detected first and their translation is searched for the translated string. Translation of the conflicting substring is appended in [] (if a string has several translations, all are appended).

If none of these switches are used, all messages are exported.

There are modifier switches influencing the output:

`-a`: Do not abbreviate tags. Normally, tags are abbreviated, which simplifies translation. Makes sense in Help, where tags are often very complex. Example:

```
Your text was corrected by <link href=""text/shared/01/06040000.xhp"" name=""Autocorrect"">Autocorrect</link> so that single quotation marks were replaced by <link href=""text/shared/01/06040400.xhp"" name=""typographical quotation marks"">typographical quotation marks</link>.
```
is abbreviated to:
```
Your text was corrected by <LI0>Autocorrect</LI> so that double quotation marks were replaced by <LI1>typographical quotation marks</LI>
```
Abbreviations are removed on import.

`-e`: Automatically translate substrings found in the 'ui' component. Based heuristics substrings which appear as UI strings are detected. A new column in output is added, with these substrings translated. These mixed strings can serve as a reference or can be translated by any of the machine translation services. If a translation is ambiguous, all possibilities are shown.

`-x lang{,lang}` Extra language to add to the export as reference (no space after ,). An additional column (columns) will be added to the export for reference.

## Usage scenarios
### Find and correct typos
Weblate does not have a tool to find typos. The proposed procedure consists of several steps: export strings, find typos by a spell-checker and correct the typos using the `sed` editor.
1. Export all strings without accelerators

`potrans.py -p sk -a export >en_sk.csv`

Open the `en_sk.csv` file in LibreOffice, delete columns 1 - 3 (File name, Key ID, English strings) and save as `sk.csv`
#### 1. Find typos
Run this script:
```
cat sk.csv |tr " " "\n" | tr "/-" "\n"| tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//"|sort|uniq|aspell -l sk list
```
The scripts breaks lines in single words (`tr " " "\n" | tr "/-" "\n"`), removes special characters (`tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//">typos.txt`), finds unique words (`sort|uniq`) and finally uses the `aspell` spellchecker to find misspelled words. The output has one misspelled word on each line. Check it and eventually remove correct words.

The script was assembled in a trial-and-error way, maybe that there is a much nicer way, how to reach the same goal.

#### 2. Correct typos

1. Find the file with a typo (`typoo` below), for example with the command
```
grep typoo `find libo_ui-master -name [^.]\*.po`
```
(`[^.]` ensures the backup files are not searched). Then open the file in a text editor and fix the problem.

1. Change all typos at once using the `sed` editor. For that, from the list of typos create a file, e.g.,  `fixerror.sed` with a sed command for each typo in the form
```
s/typoo/typo/
```
and run
```
for i in `find libo_ui-master -name [^.]\*.po`; do sed -i -f fixerrors.sed $i; done`
```
(if using the `bash` shell)

#### 3. Check the changes
Check the changes by means of the `potrans.py -p ui diff` command. If something went wrong revert the changes (`potrans.pu -p ui re`), modify the sed file and run `sed` again.

#### 4. Upload the modifications
Upload the modifications by `potrans.py -p ui up` to the Weblate server.

## Translate strings using Google translate
Translation services as Google translate make sense only for longer text strings composed of sentences. GUI translation should be done directly in Weblate.
### 1. Export the desired substrings
Use the `export` command (eventually with one of its switches). If necessary, sort the CSV file according to text length and delete rows short on text.
### 2. Use the translation service
Using LibreOffice, copy some rows in the Source column and translate them using https://translate.google.com/. Copy the translation to the Target column.
### 3. Check and modify the translation
### 4. Import the translation
Import the translated CSV file using `potrans.py -p help -c infile.csv im`. The Google translate service adds a large amount of spaces (around tags, operators, the $ and % characters which a part of variables). These are removed upon import. This removal is probably not perfect, but if it happens to merge words, the import process is aborted and an error message with instructions is displayed.

# dialogtrans.py
The script renders LibreOffice dialogs (*.ui files) and stores them as a PNG image with a pair of renditions: an English original (with strings supplemented by a corresponding key_id) and translated version:
<img src="img/updatedialog.png" width="800px" height="auto">

## The procedure
1. Copy the `libreofficedevX.Y/share/config/soffice.cfg` directory to the working directory
1. Download the weblate ui project using `potrans.py -p ui down` to the working directory
1. Run the script by `dialogtrans.py  soffice.cfg/xxx > trans.csv` to render all UI files in the `soffice.cfg/xxx` subdirectory (you may specify a single UI file to render just that)
1. Check the PNG renderings in `soffice.cfg/xxx/ui`, modify translations in trans.csv
1. Import `trans.csv` with `potrans.py -p ui -c trans.csv im`
1. Upload modified translation with `potrans.py -p ui up`

## Created files
1. A CSV file with all translatable strings is written to standard output. It may be modified and imported by the `potrans.py` tool.
1. For each UI file its two versions are created, with the `-key.ui` and `-lang.ui` suffix. They may be opened by the `glade` tool.
1. For each UI file a PNG image with its rendition is created.
