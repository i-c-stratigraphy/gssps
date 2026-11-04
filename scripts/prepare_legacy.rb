require 'yaml'
require 'fileutils'
source, config_path = ARGV
abort 'Usage: prepare_legacy.rb SOURCE CONFIG' unless source && config_path
config = YAML.load_file("#{source}/_config.yml")
config.delete('theme')
config['exclude'] = %w[README.md DEPLOYMENT.md vendor scripts data .env .env.example]
File.write(config_path, config.to_yaml)
# The original custom page shell handles the old theme; Minima was used only
# for the starter post and error page. Supply those missing fallback layouts.
layout = File.file?("#{source}/_layouts/page.html") ? 'page' : 'guide'
%w[post default].each do |name|
  path = "#{source}/_layouts/#{name}.html"
  File.write(path, "---\nlayout: #{layout}\n---\n{{ content }}\n") unless File.exist?(path)
end
