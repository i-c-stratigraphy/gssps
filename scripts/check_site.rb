require 'yaml'
require 'date'
require 'json'
root = ARGV.fetch(0, 'current-site')
pages = Dir['pages/**/*.{md,html}']
count = 0
pages.each do |path|
  text = File.read(path)
  next unless text.start_with?("---\n")
  metadata = YAML.safe_load(text.split("---", 3)[1], permitted_classes: [Date]) if defined?(Date)
  metadata ||= YAML.safe_load(text.split("---", 3)[1])
  route = metadata['permalink'] || "/#{path.sub(/\.[^.]+$/, '.html')}"
  name = route.delete_prefix('/')
  candidates = ["#{root}/#{name}", "#{root}/#{name}/index.html", "#{root}/#{name}.html"]
  candidates.unshift("#{root}/index.html") if name.empty?
  output = candidates.find { |candidate| File.file?(candidate) }
  raise "Missing output for #{path}" unless output
  html = File.read(output)
  raise "Nested HTML document: #{path}" unless html.scan(/<html\b/).length == 1
  raise "Theme missing: #{path}" unless html.include?('id="navMenu"') && html.include?('id="ics-banner"')
  raise "Nested project prefix: #{path}" if html.match?(%r{/(guide|gssps)/(guide|gssps)/})
  count += 1
end
if File.file?('_layouts/table.html')
  source = File.read('_layouts/table.html')
  rendered = File.read("#{root}/index.html")
  raise 'GSSP table rows lost' unless source.scan('data-record=').length == rendered.scan('data-record=').length
  json = rendered[/<script id="gssps-map-data"[^>]*>(.*?)<\/script>/m, 1]
  raise 'GSSP map points lost' unless JSON.parse(json)['features'].length == JSON.parse(File.read('gssps.geojson'))['features'].length
end
puts "PASS: #{count} themed page routes; GSSP records/map retained where applicable."
