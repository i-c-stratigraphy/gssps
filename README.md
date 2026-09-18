# ICS' GSSPs
This repository contains the source code for the International Commission on Stratigraphy (ICS)'s website about Global Boundary Stratotype Section (GSSP)s, online at <http://stratigraphy.org/gssps>. 

## Technical notes
This is a [Jekyll](https://jekyllrb.com/) *static site generator* website which means the source files are pretty much simplified HTML pages - [Markdown](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)-formatted text files which you can see stored in the [pages/](pages/) folder. These are combined with a very simple template to add headers & footers to all pages and produce the final HTML web pages which are then delivered online with a web server. We are using the built in [GitHub Pages](https://pages.github.com/).

### Jekyll Commands
#### Launch new site
```
jekyll new . --force
```

#### Serve locally
Create `.env` in the repository root (see `.env.example`) and set
`MAPBOX_ACCESS_TOKEN` to your public Mapbox token, then run:

```
bundle exec jekyll serve
```

The Jekyll plugin reads `.env` automatically. An existing
`MAPBOX_ACCESS_TOKEN` environment variable takes precedence. Restart Jekyll
after changing the token. `.env` is ignored by Git and excluded from the site.
The token is embedded in the browser's map code, so use a public Mapbox token.

#### Deploy to GitHub Pages
Set the repository Actions secret `MAPBOX_ACCESS_TOKEN` and select **GitHub
Actions** under **Settings → Pages → Build and deployment → Source**.
The workflow in `.github/workflows/pages.yml` builds and deploys on pushes to
`master`, or can be started manually. It passes the secret to the same Jekyll
plugin; GitHub builds never fall back to `.env`. A missing token fails the build
with an explanatory message.

_to fx dependencies:_
```
bundle update && bundle install
```


## License & Rights
The content of this repository is licensed using the Creative Commons Attribution 4.0 license:

* <https://creativecommons.org/licenses/by/4.0/>

See the [local copy of the license deed](LICENSE) for details.

&copy; International Commission on Stratigraphy, all rights reserved


## Support and contacts
*For website technical matters:*  
**Nicholas Car**  
<nick@kurrawong.ai>
