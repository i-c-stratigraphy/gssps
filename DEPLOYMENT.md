# Website publication

Pushes to master publish the themed site at https://stratigraphy.org/gssps/ using GitHub Actions.
The workflow also builds the frozen original revision 9d8d2fc4e1282834d1dd754cfa29a7ec36aafa8f under /gssps/old/.
Keep Settings → Pages configured for GitHub Actions; branch publishing would remove the archive.

Shared ICS includes, navigation, images and SCSS match the main website's Bulma Clean Theme.
GSSP tables, embedded map records, existing page routes and file downloads are preserved.
The Mapbox token comes from the existing MAPBOX_ACCESS_TOKEN Actions secret; local builds use .env.
Environment files and source tooling are excluded from the published artifact.

The generator's table_page_template.html uses the theme layout so data regeneration retains the theme.
The legacy build uses the maintained Ruby dependencies and original custom page layout.
The assembly script rebases local archive URLs and verifies that current files are unchanged.
Pull requests build and validate without deploying. Run the archive tests with:

    ruby scripts/test_assemble_sites.rb
