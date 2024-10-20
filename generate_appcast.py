import sys
import requests
from lxml import etree as ET
from xml.dom import minidom
import argparse
import markdown

# GitHub repository details (owner and repo name)
GITHUB_REPO_OWNER = "borgbase"
GITHUB_REPO_NAME = "vorta"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases"

# Function to fetch release information using the GitHub API
def fetch_github_releases():
    response = requests.get(GITHUB_API_URL)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch releases: {response.status_code}")

# Function to create Appcast XML
def generate_appcast_xml(releases, include_prereleases=False):
    nsmap = {
        'sparkle': "http://www.andymatuschak.org/xml-namespaces/sparkle",
        'dc': "http://purl.org/dc/elements/1.1/"
    }
    # ET.register_namespace('sparkle', "http://www.andymatuschak.org/xml-namespaces/sparkle")
    rss = ET.Element("rss", version="2.0", nsmap=nsmap)
    channel = ET.SubElement(rss, "channel")

    # Required fields for the Appcast
    title = ET.SubElement(channel, "title")
    title.text = "Vorta Updates"
    link = ET.SubElement(channel, "link")
    link.text = f"https://borgbase.github.io/vorta/{args.output}"  # Change to your actual Appcast URL
    description = ET.SubElement(channel, "description")
    description.text = "Latest updates for the app."
    language = ET.SubElement(channel, "language")
    language.text = "en"

    # Add release entries to the Appcast
    for release in releases:
        if not include_prereleases and release['prerelease']:
            continue  # Skip pre-releases if not requested

        item = ET.SubElement(channel, "item")

        item_title = ET.SubElement(item, "title")
        item_title.text = release['tag_name']

        item_description = ET.SubElement(item, "description")
        item_description.text = ET.CDATA(markdown.markdown(release.get("body", "No release notes available")))

        pub_date = ET.SubElement(item, "pubDate")
        pub_date.text = release["published_at"]

        sparkle_version = ET.SubElement(item, ET.QName(nsmap['sparkle'], 'version'))
        sparkle_version.text = release['tag_name'][1:]

        sparkle_releasenotes = ET.SubElement(item, ET.QName(nsmap['sparkle'], 'releaseNotesLink'))
        sparkle_releasenotes.text = release['html_url']

        # Add enclosure for attached assets (assuming one main asset per release)
        for asset in release.get("assets", []):
            enclosure = ET.SubElement(item, "enclosure", url=asset['browser_download_url'], length=str(asset['size']), type=asset['content_type'])
            # enclosure.set(ET.QName(nsmap['sparkle'], 'version'), release['tag_name'][1:])
            break  # Include only one main file per release, remove break for multiple

    # Convert the XML tree to a nicely formatted string
    return ET.tostring(rss, pretty_print=True, xml_declaration=True, encoding="UTF-8")

# Function to handle the creation of the appcast XML file
def write_appcast_to_file(appcast_xml, filename):
    with open(filename, "w") as file:
        file.write(appcast_xml.decode('utf-8'))
    print(f"Appcast XML written to {filename}")


if __name__ == "__main__":
    # Argument parser for handling command-line options
    parser = argparse.ArgumentParser(description="Generate Appcast XML from GitHub releases.")
    parser.add_argument(
        '--include-prereleases',
        action='store_true',
        help='Include pre-releases'
    )
    parser.add_argument(
        'output',
        type=str,
        help='Output file to write to. Usually appcast.xml or appcast-pre.xml'
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as exc:
        print(f"Error: {exc}")
        parser.print_help()
        sys.exit(1)

    # Step 1: Fetch GitHub releases using the GitHub API
    releases = fetch_github_releases()

    # Step 2: Generate Appcast XML for stable releases
    appcast_xml = generate_appcast_xml(releases, include_prereleases=args.include_prereleases)

    # Step 3: Write stable releases to the specified output file
    write_appcast_to_file(appcast_xml, args.output)
