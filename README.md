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
```
bundle exec jekyll serve
```

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
