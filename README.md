# Anknotes (Evernote to Anki Importer)
**Forks and suggestions are very welcome.**

##Outline 
1. [Description] (#description)
1. [User Instructions] (#user-instructions)
1. [Current Features] (#current-features)
1. [Settings] (#settings)
1. [Details] (#details)
	* [Templates] (#anki-templates)
	* [Auto Import] (#auto-import)
	* [Note Processing] (#note-processing-features)
1. [Beta Functions] (#beta-functions)
1. [See Also Footer Links] (#see-also-footer-links)
1. [Future Features] (#future-features)
1. [Developer Notes] (#developer-notes)

## Description
An Anki plug-in for downloading Evernote notes to Anki directly from Anki. In addition to this core functionality, Anknotes can automatically modify Evernote notes, create new Evernote notes, and link related Evernote notes together.

## User Instructions
1. Download everything, move it to your `Anki/addons` directory
1. Start Anki, and click the Menu Item `Anknotes → Import From Evernote`
	- Optionally, you can customize [settings] (#settings) in the Anknotes tab in Anki's preferences
1. When you run it the first time a browser tab will open on the Evernote site asking you for access to your account
	- When you click okay you are taken to a website where the OAuth verification key is displayed.  You paste that key into the open Anki prompt and click okay.
	- Note that for the first 24 hours after granting access, you have unlimited API usage. After that, Evernote applies rate limiting. 
	- So, sync everything immediately!

## Current Features
#### Evernote Importing 
- A rich set of [options] (#settings) will dynamically generate your query from tags, notebook, title, last updated date, or free text 
- Free text can include any valid [Evernote query] (https://dev.evernote.com/doc/articles/search_grammar.php)
- [Auto Import] (#auto-import) is possible

#### Anki Note Generation
- [Four types of Anki Notes] (#anki-templates) can be generated:
	- Standard, Reversible, Reverse-Only, and Cloze
- [Post-process] (#note-processing-features) Evernote Notes with a few improvements
	- [Fix Evernote note links] (#post-process-links)
	- [Automatically embed images] (#post-process-images)
	- [Occlude certain text] (#post-process-occlude) on fronts of Anki cards
	- [Generate Cloze Fields] (#post-process-cloze)
	- [Process a "See Also" Footer field] (#see-also-footer-links) for showing links to other Evernote notes 
- See the [Beta Functions] (#beta-functions) section below for info on See Also Footer fields, Table of Contents notes, and Outline notes 	

## Settings
#### Evernote Query
- You can enter any valid Evernote Query in the `Search Terms` field 
- The check box before a given text field enables or disables that field 
- Anknotes requires **all fields match** by default. 
	- You can use the `Match Any Terms` option to override this, but see the Evernote documentation on search for limitations 

### Pagination 
- Controls the offset parameter of the Evernote search. 
- Auto Pagination is recommended and on by default 

#### Anki Note Options
- Controls what is saved to Anki 
- You can change the base Anki deck 
	- Anknotes can append the base deck with the Evernote note's Notebook Stack and Notebook Name 
	- Any colon will be converted to two colons, to enable Anki's sub-deck functionality 
- You can change which Evernote tags are saved 
	
#### Note Updating 
- By default, Anknotes will update existing Anki notes in place. This preserves all Anki statistics. 
- You can also ignore existing notes, or delete and re-add existing notes (this will erase any Anki statistics)
	
## Details
#### Anki Templates
- All use an advanced Anki template with customized content and CSS
- Reversible notes will generate a normal and reversed card for each note
	- Add `#Reversible` tag to Evernote note before importing 
- Reverse-only notes will only generate a reversed card 
	- Add `#Reverse-Only` tag to Evernote note before importing 
- [Cloze notes] (#post-process-cloze) are automatically detected by Anknotes

#### Auto Import
1. Automatically import on profile load 	
	- Enable via Anknotes Menu 
	- Auto Import will be delayed if an import has occurred in the past 30 minutes 
1. Automatically page through an Evernote query
	- Enable via Anknotes Settings 
	- Evernote only returns 250 results per search, so queries with > 250 possible results require multiple searches 
	- If more than 10 API calls are made during a search, the next search is delayed by 15 minutes 
1. Automatically import continuously
	- Only configurable via source code at this time
	- Enable Auto Import and Pagination as per above, and then modify `constants.py`, setting `PAGING_RESTART_WHEN_COMPLETE` to `True`		

#### Note Processing Features
1. Fix [Evernote Note Links] (https://dev.evernote.com/doc/articles/note_links.php) so that they can be opened in Anki
	- Convert "New Style" Evernote web links to "Classic" Evernote in-app links so that any note links open directly in Evernote 
	- Convert all Evernote links to use two forward slashes instead of three to get around an Anki bug	
1. Automatically embed images
	- This is a workaround since Anki cannot import Evernote resources such as embedded images, PDF files, sounds, etc
	- Anknotes will convert any of the following to embedded, linkable images:
		- Any HTML Dropbox sharing link to an image `(https://www.dropbox.com/s/...)`
		- Any Dropbox plain-text to an image (same as above, but plain-text links must end with `?dl=0` or `?dl=1`)
		- Any HTML link with Link Text beginning with "Image Link", e.g.: `<a href='http://www.foo.com/bar'>Image Link #1</a>`	
1. Occlude (hide) certain text on fronts of Anki cards
	- Useful for displaying additional information but ensuring it only shows on backs of cards
	- Anknotes converts any of the following to special text that will display in grey color, and only on the backs of cards:
		- Any text with white foreground
		- Any text within two brackets, such as `<<Hide Me>>`	
1. Automatically generate [Cloze fields] (http://ankisrs.net/docs/manual.html#cloze)
	- Any text with a single curly bracket will be converted into a cloze field
		- E.g., two cloze fields are generated from: The central nervous system is made up of the `{brain}` and `{spinal cord}`
	- If you want to generate a single cloze field (not increment the field #), insert a pound character `('#')` after the first curly bracket:
		- E.g., a single cloze field is generated from: The central nervous system is made up of the `{brain}` and `{#spinal cord}`
		
##Beta Functions
#### Note Creation 
- Anknotes can create and upload/update existing Evernote notes 
- Currently this is limited to creating new Auto TOC notes and modifying the See Also Footer field of existing notes 
- Anknotes uses client-side validation to decrease API usage, but there is currently an issue with use of the validation library in Anki. 
	- So, Anknotes will execute this validation using an **external** script, not as an Anki addon 
	- Therefore, you must **manually** ensure that **Python** and the **lxml** module is installed on your system 
	- Alternately, disable validation: Edit `constants.py` and set `ENABLE_VALIDATION` to `False`

#### Find Deleted/Orphaned Notes 
- Anknotes is not intended for use as a sync client with Evernote (this may change in the future)
- Thus, notes deleted from the Evernote servers will not be deleted from Anki
- Use `Anknotes → Maintenance Tasks → Find Deleted Notes` to find and delete these notes from Anki
	- You can also find notes in Evernote that don't exist in Anki 
	- First, you must create a "Table of Contents" note using the Evernote desktop application:
		- In the Windows client, select ALL notes you want imported into Anki, and click the `Create Table of Contents Note` button on the right-sided panel
		- Alternately, select 'Copy Note Links' and paste the content into a new Evernote Note. 
	- Export your Evernote note to `anknotes/extra/user/Table of Contents.enex`
	
## "See Also" Footer Links
#### Concept 
- You have topics (**Root Notes**) broken down into multiple sub-topics (**Sub Notes**)
	- The Root Notes are too broad to be tested, and therefore not useful as Anki cards 
	- The Sub Notes are testable topics intended to be used as Anki cards 
- Anknotes tries to link these related Sub Notes together so you can rapidly view related content in Evernote 

#### Terms 
1. **Table of Contents (TOC) Notes**
	- Primarily contain a hierarchical list of links to other notes
2. **Outline Notes**
	- Primarily contain content itself of sub-notes
	- E.g. a summary of sub-notes or full text of sub-notes
	- Common usage scenario is creating a broad **Outline** style note when studying a topic, and breaking that down into multiple **Sub Notes** to use in Anki
3. **"See Also" Footer** Fields 
	- Primarily consist of links to TOC notes, Outline notes, or other Evernote notes 
4. **Root Titles** and **Sub Notes**
	- Sub Notes are notes with a colon in the title 
	- Root Title is the portion of the title before the first colon
	
#### Integration 
###### With Anki:
- The **"See Also" Footer** field is shown on the backs of Anki cards only, so having a descriptive link in here won't give away the correct answer
- The content itself of **TOC** and **Outline** notes are also viewable on the backs of Anki cards 

##### With Evernote:
- Anknotes can create new Evernote notes from automatically generated TOC notes
- Anknotes can update existing Evernote notes with modified See Also Footer fields

#### Usage
###### Manual Usage: 
- Add a new line to the end of your Evernote note that begins with `See Also`, and include relevant links after it
- Tag notes in Evernote before importing. 
	- Table of Contents (TOC) notes are designated by the `#TOC` tag. 
	- Outline notes are designed by the `#Outline` tag. 

###### Automated Usage: 
- Anknotes can automatically create:
	- Table of Contents Notes
		- Created for **Root Titles** containing two or more Sub Notes
		- In Anki, click the `Anknotes Menu → Process See Also Footer Links → Step 3: Create Auto TOC Notes`. 
		- Once the Auto TOC notes are generated, click `Steps 4 & 5` to upload the notes to Evernote 
	- See Also' Footer fields for displaying links to other Evernote notes
		- Any links from other notes, including automatically generated TOC notes, are inserted into this field by Anknotes
	- Creation of Outline notes from sub-notes or sub-notes from outline notes is a possible future feature 

#### Example:
Let's say we have nine **Sub Notes** titled `Diabetes: Symptoms`, `Diabetes: Treatment`, `Diabetes: Treatment: Types of Insulin`, and `Diabetes: Complications`, etc:
- Anknotes will generate a TOC note **`Diabetes`** with hierarchical links to all nine sub-notes as such:

	>	 	DIABETES
	>		  	1. Symptoms 
	>		  	2. Complications 
	>			 	1. Cardiovascular
	>		 			* Heart Attack Risk 
	>				2. Infectious
	>	 			3. Ophthalmologic
	>		  	3. Treatment 
	>		 		* Types of Insulin	

- Anknotes can then insert a link to that TOC note in the 'See Also' Footer field of the sub notes 
- This 'See Also' Footer field will display on the backs of Anki cards 
- The TOC note's contents themselves will also be available on the backs of Anki cards

## Future Features
- More robust options
	- Move options from source code into GUI
	- Allow enabling/disabling of beta functions like See Also fields 
	- Customize criteria for detecting see also fields
- Implement full sync with Evernote servers 
- Import resources (e.g., images, sounds, etc) from Evernote notes
- Automatically create Anki sub-notes from a large Evernote note
	
## Developer Notes
#### Anki Template / CSS Files:
- Template File Location: `/extra/ancillary/FrontTemplate.htm`
- CSS File Location: `/extra/ancillary/_AviAnkiCSS.css`
- Message Box CSS: `/extra/ancillary/QMessageBox.css`

#### Anknotes Local Database
- Anknotes saves all Evernote notes, tags, and notebooks in the SQL database of the active Anki profile 
	- You may force a resync with the local Anknotes database via the menu: `Anknotes → Maintenance Tasks`
	- You may force update of ancillary tag/notebook data via this menu 
- Maps of see also footer links and Table of Contents notes are also saved here 
- All Evernote note history is saved in a separate table. This is not currently used but may be helpful if data loss occurs or for future functionality 

#### Developer Functions 
- If you are testing a new feature, you can automatically have Anki run that function when Anki starts.
	- Simply add the method to `__main__.py` under the comment `Add a function here and it will automatically run on profile load`
	- Also, create the folder `/anknotes/extra/dev` and add files `anknotes.developer` and `anknotes.developer.automate`	