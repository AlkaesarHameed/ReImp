import{a as N,b as $,c as U}from"./chunk-LR7J46YX.js";import"./chunk-JA2DIW7E.js";import{a as Y,b as j}from"./chunk-ZMZXLXSM.js";import"./chunk-L7CYZS6T.js";import{a as G,b as Q}from"./chunk-RANQPQCM.js";import"./chunk-GGQ7LRWG.js";import"./chunk-SILQIBBA.js";import{n as H}from"./chunk-CMI2WP65.js";import"./chunk-F2X3VGZZ.js";import{b as W,e as R,g as V,p as B}from"./chunk-COAKLJSO.js";import{e as z}from"./chunk-TD2OOY6M.js";import"./chunk-R72WXHZK.js";import{u as L}from"./chunk-2QNP6Q64.js";import{Ab as f,Ac as D,Bb as t,Cb as n,Db as c,Hb as _,Kb as h,Lb as m,Ta as k,Tb as r,Ub as w,Vb as M,Xa as s,Yb as F,Zb as I,_b as A,fb as q,ka as y,kb as g,la as C,sb as p,ub as T,wb as x,xb as b,ya as v,yb as E,zb as u}from"./chunk-UUFN4DK2.js";import{a as S,b as O}from"./chunk-4CLCTAJ7.js";var X=(i,l)=>l.name,J=(i,l)=>l.id;function K(i,l){if(i&1){let e=_();t(0,"button",31),h("click",function(){y(e);let o=m();return C(o.clearSearch())}),c(1,"i",32),n()}}function Z(i,l){if(i&1&&(t(0,"p",9),r(1),n()),i&2){let e=m();s(),M(" Found ",e.filteredCategories().length," categories with matching questions ")}}function ee(i,l){if(i&1){let e=_();t(0,"button",33),h("click",function(){let o=y(e).$implicit,d=m();return C(d.scrollToCategory(o.name))}),c(1,"i"),t(2,"span"),r(3),n(),t(4,"span",34),r(5),n()()}if(i&2){let e=l.$implicit,a=m();T("active",a.activeCategory()===e.name),s(),x("pi "+e.icon),s(2),w(e.name),s(2),w(a.getCategoryCount(e.name))}}function te(i,l){if(i&1&&c(0,"p-tag",41),i&2){let e=l.$implicit;p("value",e)("rounded",!0)}}function ie(i,l){if(i&1&&(t(0,"div",38)(1,"span",39),r(2),n(),t(3,"div",40),u(4,te,1,2,"p-tag",41,E),n()()),i&2){let e=m().$implicit;s(2),w(e.question),s(2),f(e.tags)}}function ne(i,l){if(i&1&&(t(0,"p-accordionTab"),g(1,ie,6,1,"ng-template",36),c(2,"div",37),n()),i&2){let e=l.$implicit;s(2),p("innerHTML",e.answer,k)}}function oe(i,l){if(i&1&&(t(0,"div",13)(1,"h3"),c(2,"i"),r(3),n(),t(4,"p-accordion",35),u(5,ne,3,1,"p-accordionTab",null,J),n()()),i&2){let e=l.$implicit;p("id","category-"+e.name.toLowerCase().replace(" ","-")),s(2),x("pi "+e.icon),s(),M(" ",e.name," "),s(),p("multiple",!0),s(),f(e.items)}}function re(i,l){if(i&1){let e=_();t(0,"div",14),c(1,"i",6),t(2,"h4"),r(3,"No matching questions found"),n(),t(4,"p"),r(5,"Try adjusting your search terms or browse all categories"),n(),t(6,"button",42),h("click",function(){y(e);let o=m();return C(o.clearSearch())}),r(7," Clear Search "),n()()}}var we=(()=>{class i{searchQuery=v("");activeCategory=v("");allCategories=[{name:"General",icon:"pi-info-circle",items:[{id:"g1",question:"What is the Claims Processing System?",answer:"The Claims Processing System is a comprehensive healthcare claims management platform designed to streamline the submission, processing, and adjudication of medical claims. It supports <strong>HIPAA-compliant</strong> workflows and real-time eligibility verification.",category:"General",tags:["overview","basics"]},{id:"g2",question:"What browsers are supported?",answer:`The system supports all modern browsers including:
            <ul>
              <li>Google Chrome (recommended)</li>
              <li>Mozilla Firefox</li>
              <li>Microsoft Edge</li>
              <li>Safari (macOS)</li>
            </ul>
            For the best experience, we recommend using the latest version of Chrome.`,category:"General",tags:["requirements","browser"]},{id:"g3",question:"How do I change my password?",answer:`To change your password:
            <ol>
              <li>Click on your profile icon in the top right corner</li>
              <li>Select "Account Settings"</li>
              <li>Click "Change Password"</li>
              <li>Enter your current password and new password</li>
              <li>Click "Update Password"</li>
            </ol>
            Passwords must be at least 12 characters with uppercase, lowercase, numbers, and special characters.`,category:"General",tags:["account","security"]},{id:"g4",question:"Why does my session keep timing out?",answer:`For <strong>HIPAA compliance</strong>, sessions automatically expire after 15 minutes of inactivity. This protects sensitive healthcare information. To prevent losing work:
            <ul>
              <li>Save drafts frequently when entering claims</li>
              <li>Stay active in the application</li>
              <li>Log back in to restore your session</li>
            </ul>`,category:"General",tags:["security","session"]}]},{name:"Claims",icon:"pi-file",items:[{id:"c1",question:"How do I submit a new claim?",answer:`To submit a new claim:
            <ol>
              <li>Click "Submit Claim" from the dashboard or navigate to Claims > New</li>
              <li>Enter member information and verify eligibility</li>
              <li>Select the rendering and billing provider</li>
              <li>Add diagnosis codes (ICD-10) and service lines</li>
              <li>Review all information and click Submit</li>
            </ol>
            For detailed steps, see the <strong>Examples</strong> section.`,category:"Claims",tags:["submission","how-to"]},{id:"c2",question:"What claim types are supported?",answer:`The system supports multiple claim types:
            <ul>
              <li><strong>Professional (CMS-1500)</strong>: Physician and outpatient services</li>
              <li><strong>Institutional (UB-04)</strong>: Hospital and facility claims</li>
              <li><strong>Dental</strong>: Dental procedure claims</li>
              <li><strong>Pharmacy</strong>: Prescription drug claims</li>
            </ul>`,category:"Claims",tags:["types","CMS-1500","UB-04"]},{id:"c3",question:"How can I check the status of my claim?",answer:`To check claim status:
            <ol>
              <li>Navigate to Claims from the main menu</li>
              <li>Use filters to search by claim ID, member, or date range</li>
              <li>Click on a claim to view detailed status</li>
            </ol>
            The claim detail page shows current status, processing history, and any required actions.`,category:"Claims",tags:["status","tracking"]},{id:"c4",question:"Why was my claim denied?",answer:`Claims can be denied for various reasons:
            <ul>
              <li><strong>Eligibility</strong>: Member not covered on date of service</li>
              <li><strong>Authorization</strong>: Missing or invalid prior authorization</li>
              <li><strong>Duplicate</strong>: Claim already processed</li>
              <li><strong>Coding</strong>: Invalid or mismatched codes</li>
              <li><strong>Timely Filing</strong>: Submitted after deadline</li>
            </ul>
            Check the denial reason code on the claim for specific details. Most denials can be appealed within 180 days.`,category:"Claims",tags:["denial","troubleshooting"]},{id:"c5",question:"Can I save a claim as a draft?",answer:`Yes! You can save a claim as a draft at any point during submission:
            <ul>
              <li>Click "Save Draft" at the bottom of any wizard step</li>
              <li>Drafts are saved to your account and can be resumed later</li>
              <li>Access saved drafts from Claims > My Drafts</li>
              <li>Drafts are automatically saved every 60 seconds</li>
            </ul>
            Drafts are retained for 30 days.`,category:"Claims",tags:["draft","save"]}]},{name:"Eligibility",icon:"pi-verified",items:[{id:"e1",question:"How do I verify member eligibility?",answer:`To verify eligibility:
            <ol>
              <li>Navigate to Eligibility from the main menu</li>
              <li>Enter the member ID or search by name/DOB</li>
              <li>Select the date of service</li>
              <li>View coverage details, benefits, and limitations</li>
            </ol>
            You can also check eligibility during claim submission.`,category:"Eligibility",tags:["verification","how-to"]},{id:"e2",question:"What information does eligibility verification show?",answer:`Eligibility verification displays:
            <ul>
              <li><strong>Coverage Status</strong>: Active, terminated, or pending</li>
              <li><strong>Plan Information</strong>: Plan name, type, and network</li>
              <li><strong>Benefits</strong>: Deductibles, copays, coinsurance</li>
              <li><strong>Accumulators</strong>: Deductible met, out-of-pocket status</li>
              <li><strong>Limitations</strong>: Exclusions and waiting periods</li>
              <li><strong>Prior Auth</strong>: Services requiring authorization</li>
            </ul>`,category:"Eligibility",tags:["coverage","benefits"]},{id:"e3",question:'What does "eligibility not found" mean?',answer:`This error typically means:
            <ul>
              <li>Incorrect member ID entered</li>
              <li>Member not enrolled on the selected date</li>
              <li>Member data not yet loaded in the system</li>
              <li>Dependent entered without subscriber info</li>
            </ul>
            Try searching by name and DOB instead, or verify the member ID with enrollment.`,category:"Eligibility",tags:["error","troubleshooting"]}]},{name:"Payments",icon:"pi-dollar",items:[{id:"p1",question:"When will payment be issued?",answer:`Payment timelines depend on claim type:
            <ul>
              <li><strong>Clean Claims</strong>: Payment within 30 days of receipt</li>
              <li><strong>Pended Claims</strong>: After manual review completion</li>
              <li><strong>Electronic (EFT)</strong>: 2-3 business days after approval</li>
              <li><strong>Paper Check</strong>: 7-10 business days after approval</li>
            </ul>`,category:"Payments",tags:["timeline","EFT"]},{id:"p2",question:"How do I sign up for electronic payments?",answer:`To enroll in EFT payments:
            <ol>
              <li>Contact Provider Services at 1-800-123-4567</li>
              <li>Complete the EFT enrollment form</li>
              <li>Provide banking information and tax ID</li>
              <li>Allow 2-3 weeks for processing</li>
            </ol>
            EFT payments are faster and more secure than paper checks.`,category:"Payments",tags:["EFT","enrollment"]},{id:"p3",question:"What is an ERA/835?",answer:`An <strong>ERA (Electronic Remittance Advice)</strong> or <strong>835 transaction</strong> is the electronic version of an Explanation of Benefits. It contains:
            <ul>
              <li>Payment details for each claim line</li>
              <li>Adjustment reason codes</li>
              <li>Patient responsibility amounts</li>
              <li>Remark codes with additional information</li>
            </ul>
            ERAs can be downloaded from the Reports section or received via clearinghouse.`,category:"Payments",tags:["ERA","835","remittance"]}]},{name:"Technical",icon:"pi-cog",items:[{id:"t1",question:"What file formats are supported for attachments?",answer:`Supported attachment formats include:
            <ul>
              <li><strong>Documents</strong>: PDF, DOC, DOCX</li>
              <li><strong>Images</strong>: JPG, PNG, TIFF</li>
              <li><strong>Spreadsheets</strong>: XLS, XLSX, CSV</li>
            </ul>
            Maximum file size is 10MB per attachment, 50MB total per claim.`,category:"Technical",tags:["attachments","files"]},{id:"t2",question:"Can I integrate with my practice management system?",answer:`Yes! We offer several integration options:
            <ul>
              <li><strong>EDI/837</strong>: Standard HIPAA transactions</li>
              <li><strong>REST API</strong>: Real-time claim submission and status</li>
              <li><strong>SFTP</strong>: Batch file submission</li>
              <li><strong>Clearinghouse</strong>: Connect through your existing clearinghouse</li>
            </ul>
            Contact Technical Support for integration documentation.`,category:"Technical",tags:["integration","API","EDI"]},{id:"t3",question:"Is the system HIPAA compliant?",answer:`Yes, the system is fully <strong>HIPAA compliant</strong>:
            <ul>
              <li>256-bit AES encryption for data at rest</li>
              <li>TLS 1.3 encryption for data in transit</li>
              <li>Automatic session timeout after 15 minutes</li>
              <li>Complete audit logging of all user actions</li>
              <li>Role-based access controls</li>
              <li>Annual third-party security assessments</li>
            </ul>`,category:"Technical",tags:["HIPAA","security","compliance"]}]}];filteredCategories=D(()=>{let e=this.searchQuery().toLowerCase();return e?this.allCategories.map(a=>O(S({},a),{items:a.items.filter(o=>o.question.toLowerCase().includes(e)||o.answer.toLowerCase().includes(e)||o.tags.some(d=>d.toLowerCase().includes(e)))})).filter(a=>a.items.length>0):this.allCategories});onSearch(){}clearSearch(){this.searchQuery.set("")}getCategoryCount(e){return this.allCategories.find(o=>o.name===e)?.items.length??0}scrollToCategory(e){this.activeCategory.set(e);let a="category-"+e.toLowerCase().replace(" ","-"),o=document.getElementById(a);o&&o.scrollIntoView({behavior:"smooth"})}static \u0275fac=function(a){return new(a||i)};static \u0275cmp=q({type:i,selectors:[["app-faq"]],decls:52,vars:4,consts:[[1,"faq-page"],[1,"intro-section"],[1,"pi","pi-comments"],[1,"lead"],[1,"search-section"],[1,"search-box"],[1,"pi","pi-search"],["type","text","pInputText","","placeholder","Search questions...",3,"ngModelChange","input","ngModel"],[1,"clear-btn"],[1,"search-results"],[1,"category-links"],[1,"category-link",3,"active"],[1,"faq-categories"],[1,"faq-category",3,"id"],[1,"no-results"],[1,"support-section"],[1,"support-card"],[1,"support-content"],[1,"support-actions"],["href","mailto:support@claims.local",1,"support-btn","email"],[1,"pi","pi-envelope"],["href","tel:+18001234567",1,"support-btn","phone"],[1,"pi","pi-phone"],[1,"resources-section"],[1,"resources-grid"],["routerLink","../getting-started",1,"resource-card"],[1,"pi","pi-play"],["routerLink","../workflow",1,"resource-card"],[1,"pi","pi-sitemap"],["routerLink","../examples",1,"resource-card"],[1,"pi","pi-file-edit"],[1,"clear-btn",3,"click"],[1,"pi","pi-times"],[1,"category-link",3,"click"],[1,"count"],[3,"multiple"],["pTemplate","header"],[1,"faq-answer",3,"innerHTML"],[1,"faq-header"],[1,"question"],[1,"tags"],["severity","secondary",3,"value","rounded"],[1,"p-button","p-button-outlined",3,"click"]],template:function(a,o){a&1&&(t(0,"div",0)(1,"section",1)(2,"h2"),c(3,"i",2),r(4," Frequently Asked Questions"),n(),t(5,"p",3),r(6," Find answers to common questions about the claims processing system. Can't find what you're looking for? Contact support for assistance. "),n()(),t(7,"section",4)(8,"div",5),c(9,"i",6),t(10,"input",7),A("ngModelChange",function(P){return I(o.searchQuery,P)||(o.searchQuery=P),P}),h("input",function(){return o.onSearch()}),n(),g(11,K,2,0,"button",8),n(),g(12,Z,2,1,"p",9),n(),t(13,"section",10),u(14,ee,6,6,"button",11,X),n(),t(16,"section",12),u(17,oe,7,5,"div",13,X),g(19,re,8,0,"div",14),n(),t(20,"section",15)(21,"div",16)(22,"div",17)(23,"h3"),r(24,"Still have questions?"),n(),t(25,"p"),r(26,"Our support team is here to help. Contact us for personalized assistance."),n()(),t(27,"div",18)(28,"a",19),c(29,"i",20),t(30,"span"),r(31,"Email Support"),n()(),t(32,"a",21),c(33,"i",22),t(34,"span"),r(35,"1-800-123-4567"),n()()()()(),t(36,"section",23)(37,"h3"),r(38,"Related Resources"),n(),t(39,"div",24)(40,"a",25),c(41,"i",26),t(42,"span"),r(43,"Getting Started Guide"),n()(),t(44,"a",27),c(45,"i",28),t(46,"span"),r(47,"Workflow Documentation"),n()(),t(48,"a",29),c(49,"i",30),t(50,"span"),r(51,"Step-by-Step Examples"),n()()()()()),a&2&&(s(10),F("ngModel",o.searchQuery),s(),b(o.searchQuery()?11:-1),s(),b(o.searchQuery()?12:-1),s(2),f(o.allCategories),s(3),f(o.filteredCategories()),s(2),b(o.filteredCategories().length===0?19:-1))},dependencies:[L,B,W,R,V,z,U,$,N,H,Q,G,j,Y],styles:[".faq-page[_ngcontent-%COMP%]{max-width:1000px;margin:0 auto}section[_ngcontent-%COMP%]{margin-bottom:2rem}h2[_ngcontent-%COMP%]{display:flex;align-items:center;gap:.75rem;color:#17a2b8;margin-bottom:1rem}h3[_ngcontent-%COMP%]{display:flex;align-items:center;gap:.5rem;color:#343a40;margin-bottom:1rem}.lead[_ngcontent-%COMP%]{font-size:1.1rem;color:#6c757d;line-height:1.7}.search-section[_ngcontent-%COMP%]{margin-bottom:1.5rem}.search-box[_ngcontent-%COMP%]{position:relative;max-width:500px}.search-box[_ngcontent-%COMP%]   i.pi-search[_ngcontent-%COMP%]{position:absolute;left:1rem;top:50%;transform:translateY(-50%);color:#adb5bd}.search-box[_ngcontent-%COMP%]   input[_ngcontent-%COMP%]{width:100%;padding:.875rem 2.5rem;border:2px solid #e9ecef;border-radius:25px;font-size:1rem;transition:border-color .2s ease}.search-box[_ngcontent-%COMP%]   input[_ngcontent-%COMP%]:focus{border-color:#17a2b8;outline:none}.clear-btn[_ngcontent-%COMP%]{position:absolute;right:1rem;top:50%;transform:translateY(-50%);background:none;border:none;color:#adb5bd;cursor:pointer;padding:.25rem}.clear-btn[_ngcontent-%COMP%]:hover{color:#343a40}.search-results[_ngcontent-%COMP%]{margin-top:.75rem;color:#6c757d;font-size:.9rem}.category-links[_ngcontent-%COMP%]{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:2rem}.category-link[_ngcontent-%COMP%]{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;background:#f8f9fa;border:1px solid #e9ecef;border-radius:20px;cursor:pointer;transition:all .2s ease;font-size:.9rem;color:#495057}.category-link[_ngcontent-%COMP%]:hover{background:#e9ecef;border-color:#dee2e6}.category-link.active[_ngcontent-%COMP%]{background:#17a2b8;border-color:#17a2b8;color:#fff}.category-link[_ngcontent-%COMP%]   .count[_ngcontent-%COMP%]{background:#0000001a;padding:.1rem .4rem;border-radius:10px;font-size:.8rem}.category-link.active[_ngcontent-%COMP%]   .count[_ngcontent-%COMP%]{background:#fff3}.faq-category[_ngcontent-%COMP%]{margin-bottom:2rem;scroll-margin-top:1rem}.faq-header[_ngcontent-%COMP%]{display:flex;justify-content:space-between;align-items:center;width:100%;gap:1rem}.question[_ngcontent-%COMP%]{font-weight:500;color:#343a40;flex:1;text-align:left}.tags[_ngcontent-%COMP%]{display:flex;gap:.25rem;flex-shrink:0}[_nghost-%COMP%]     .tags .p-tag{font-size:.7rem;padding:.1rem .4rem}.faq-answer[_ngcontent-%COMP%]{color:#495057;line-height:1.7;padding:.5rem 0}.faq-answer[_ngcontent-%COMP%]   [_ngcontent-%COMP%]:deep(ul), .faq-answer[_ngcontent-%COMP%]   [_ngcontent-%COMP%]:deep(ol){margin:.75rem 0;padding-left:1.5rem}.faq-answer[_ngcontent-%COMP%]   [_ngcontent-%COMP%]:deep(li){margin-bottom:.5rem}.faq-answer[_ngcontent-%COMP%]   [_ngcontent-%COMP%]:deep(strong){color:#343a40}.faq-answer[_ngcontent-%COMP%]   [_ngcontent-%COMP%]:deep(code){background:#e9ecef;padding:.1rem .4rem;border-radius:3px;font-family:monospace;font-size:.9rem;color:#d63384}.no-results[_ngcontent-%COMP%]{text-align:center;padding:3rem;background:#f8f9fa;border-radius:10px}.no-results[_ngcontent-%COMP%]   i[_ngcontent-%COMP%]{font-size:3rem;color:#adb5bd;margin-bottom:1rem}.no-results[_ngcontent-%COMP%]   h4[_ngcontent-%COMP%]{margin:0 0 .5rem;color:#495057}.no-results[_ngcontent-%COMP%]   p[_ngcontent-%COMP%]{margin:0 0 1rem;color:#6c757d}.support-card[_ngcontent-%COMP%]{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#17a2b8,#138496);color:#fff;padding:1.5rem 2rem;border-radius:10px}.support-content[_ngcontent-%COMP%]   h3[_ngcontent-%COMP%]{margin:0 0 .25rem;color:#fff}.support-content[_ngcontent-%COMP%]   p[_ngcontent-%COMP%]{margin:0;opacity:.9}.support-actions[_ngcontent-%COMP%]{display:flex;gap:1rem}.support-btn[_ngcontent-%COMP%]{display:flex;align-items:center;gap:.5rem;padding:.75rem 1.25rem;border-radius:6px;text-decoration:none;font-weight:500;transition:all .2s ease}.support-btn.email[_ngcontent-%COMP%]{background:#fff;color:#17a2b8}.support-btn.phone[_ngcontent-%COMP%]{background:#fff3;color:#fff}.support-btn[_ngcontent-%COMP%]:hover{transform:translateY(-2px)}.resources-section[_ngcontent-%COMP%]   h3[_ngcontent-%COMP%]{padding-bottom:.5rem;border-bottom:2px solid #e9ecef}.resources-grid[_ngcontent-%COMP%]{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}.resource-card[_ngcontent-%COMP%]{display:flex;align-items:center;gap:.75rem;padding:1rem;background:#f8f9fa;border-radius:8px;text-decoration:none;color:#495057;transition:all .2s ease}.resource-card[_ngcontent-%COMP%]:hover{background:#17a2b8;color:#fff}.resource-card[_ngcontent-%COMP%]   i[_ngcontent-%COMP%]{font-size:1.25rem}@media (max-width: 768px){.support-card[_ngcontent-%COMP%]{flex-direction:column;gap:1.5rem;text-align:center}.support-actions[_ngcontent-%COMP%]{flex-direction:column;width:100%}.support-btn[_ngcontent-%COMP%]{justify-content:center}.faq-header[_ngcontent-%COMP%]{flex-direction:column;align-items:flex-start;gap:.5rem}.tags[_ngcontent-%COMP%]{align-self:flex-start}}"],changeDetection:0})}return i})();export{we as FaqComponent};
